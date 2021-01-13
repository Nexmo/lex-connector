#!/usr/bin/env python

from __future__ import absolute_import, print_function
import wave
import datetime
import argparse
import io
import logging
import os
import sys
import time
from logging import debug, info
import uuid
import cgi
import audioop

import requests
import tornado.ioloop
import tornado.websocket
import tornado.httpserver
import tornado.template
import tornado.web
import webrtcvad
from requests_aws4auth import AWS4Auth
from tornado.web import url
import json
from base64 import b64decode
from requests.packages.urllib3.exceptions import InsecurePlatformWarning
from requests.packages.urllib3.exceptions import SNIMissingWarning
from dotenv import load_dotenv
load_dotenv()

# Only used for record function

logging.captureWarnings(True)
requests.packages.urllib3.disable_warnings(InsecurePlatformWarning)
requests.packages.urllib3.disable_warnings(SNIMissingWarning)

# Constants:
MS_PER_FRAME = 20  # Duration of a frame in ms

# Global variables
conns = {}

# Environment variables, these are set in .env locally
PORT = os.getenv("PORT")


class BufferedPipe(object):
    def __init__(self, max_frames, sink):
        """
        Create a buffer which will call the provided `sink` when full.

        It will call `sink` with the number of frames and the accumulated bytes when it reaches
        `max_buffer_size` frames.
        """
        self.sink = sink
        self.max_frames = max_frames

        self.count = 0
        self.payload = b''

    def append(self, data, id):
        """ Add another data to the buffer. `data` should be a `bytes` object. """

        self.count += 1
        self.payload += data

        if self.count == self.max_frames:
            self.process(id)

    def process(self, id):
        """ Process and clear the buffer. """
        self.sink(self.count, self.payload, id)
        self.count = 0
        self.payload = b''


class LexProcessor(object):
    def __init__(self, path, rate, clip_min, aws_region, aws_id, aws_secret, requestor_id, analytics_url):
        self._aws_region = aws_region
        self._aws_id = aws_id
        self._aws_secret = aws_secret
        self.rate = rate
        self.bytes_per_frame = rate/25
        self._path = path
        self.clip_min_frames = clip_min // MS_PER_FRAME
        self.client_id = requestor_id
        self.webhook_url = analytics_url

    def process(self, count, payload, id):
        if count > self.clip_min_frames:  # If the buffer is less than CLIP_MIN_MS, ignore it
            # if 1: (to create recordings, foder ./recordings must exist)
            if logging.getLogger().level == 10:  # if we're in Debug then save the audio clip
                fn = "{}rec-{}-{}.wav".format('./recordings/', id,
                                              datetime.datetime.now().strftime("%Y%m%dT%H%M%S"))
                output = wave.open(fn, 'wb')
                output.setparams(
                    (1, 2, self.rate, 0, 'NONE', 'not compressed'))
                output.writeframes(payload)
                output.close()
                debug('File written {}'.format(fn))
            auth = AWS4Auth(self._aws_id, self._aws_secret,
                            self._aws_region, 'lex', unsign_payload=True)

            info(">>> auth:")
            info(auth)


            info('Processing {} frames for {}'.format(str(count), id))
            endpoint = 'https://runtime.lex.{}.amazonaws.com{}'.format(
                self._aws_region, self._path)
            info(endpoint)
            if self.rate == 16000:
                headers = {
                    'Content-Type': 'audio/l16; channels=1; rate=16000', 'Accept': 'audio/pcm'}
            elif self.rate == 8000:
                headers = {
                    'Content-Type': 'audio/lpcm; sample-rate=8000; sample-size-bits=16; channel-count=1; is-big-endian=false', 'Accept': 'audio/pcm'}
            else:
                info("Unsupported Sample Rate: % ".format(self.rate))
            req = requests.Request(
                'POST', endpoint, auth=auth, headers=headers)
            prepped = req.prepare()
            info('Here 01')
            info(prepped.headers)
            r = requests.post(endpoint, data=payload, headers=prepped.headers)
            info('Here 02')
            info(r.headers)
            
            if (r.headers.get('x-amz-lex-sentiment')):
                self.customer_sentiment = b64decode(r.headers['x-amz-lex-sentiment']).decode('ascii')
            else:    
                self.customer_sentiment = "Sentiment analysis is not enabled on this Lex bot or customer_transcript is empty"

            self.customer_transcript = r.headers.get('x-amz-lex-input-transcript')
            self.bot_transcript = r.headers.get('x-amz-lex-message')
            self.session_id = r.headers.get('x-amz-lex-session-id')
            # info ("customer_sentiment")
            # info (self.customer_sentiment)
            # info ("customer_transcript")
            # info (self.customer_transcript)
            # info ("bot_transcript")
            # info (self.bot_transcript)
            # info ("session_id")
            # info (self.session_id)
            self.analytics_raw = {
                "customer_transcript": str(self.customer_transcript),
                "bot_transcript": str(self.bot_transcript),
                "customer_sentiment": str(self.customer_sentiment),
                "session_id": str(self.session_id),
                "client_id": self.client_id,
                "service": "Lex"
            }
            self.analytics = json.dumps(self.analytics_raw)
            info('analytics')
            info(self.analytics)

            # Posting to analytics server
            if (self.webhook_url):
            	a = requests.post(self.webhook_url, data=self.analytics, headers={'Content-Type': 'application/json'})

            self.playback(r.content, id)
            if r.headers.get('x-amz-lex-session-attributes'):
                if json.loads(b64decode(r.headers['x-amz-lex-session-attributes'])).get('nexmo-close'):
                    conns[id].close()
        else:
            info('Discarding {} frames'.format(str(count)))

    def playback(self, response, id):
        if self.rate == 8000:
            content, _ignore = audioop.ratecv(
                response, 2, 1, 16000, 8000, None)  # Downsample 16Khz to 8Khz
        else:
            content = response
        frames = int(len(content) // self.bytes_per_frame)
        print(frames)
        info("Playing {} frames to {}".format(frames, id))
        conn = conns[id]
        pos = int(0)
        for x in range(0, frames + 1):
            newpos = int(pos + self.bytes_per_frame)
            #debug("writing bytes {} to {} to socket for {}".format(pos, newpos, id))
            data = content[pos:newpos]
            conn.write_message(data, binary=True)
            pos = newpos


class WSHandler(tornado.websocket.WebSocketHandler):
    def initialize(self):
        # Create a buffer which will call `process` when it is full:
        self.frame_buffer = None
        # Setup the Voice Activity Detector
        self.tick = None
        self.id = uuid.uuid4().hex
        self.vad = webrtcvad.Vad()
        # Level of sensitivity
        self.processor = None
        self.path = None
        self.rate = None  # default to None
        self.silence = 20  # default of 20 frames (400ms)
        conns[self.id] = self

    def open(self, path):
        info("client connected")
        debug(self.request.uri)
        self.path = self.request.uri
        self.tick = 0

    def on_message(self, message):
        # Check if message is Binary or Text
        if type(message) != str:
            if self.vad.is_speech(message, self.rate):
                debug("SPEECH from {}".format(self.id))
                self.tick = self.silence
                self.frame_buffer.append(message, self.id)
            else:
                debug("Silence from {} TICK: {}".format(self.id, self.tick))
                self.tick -= 1
                if self.tick == 0:
                    # Force processing and clearing of the buffer
                    self.frame_buffer.process(self.id)
        else:
            info(message)
            # Here we should be extracting the meta data that was sent and attaching it to the connection object
            data = json.loads(message)
            m_type, m_options = cgi.parse_header(data['content-type'])
            
            self.rate = int(m_options['rate'])
            # info(">>> rate")
            # info(self.rate)            

            region = data.get('aws_region', 'us-east-1')
            clip_min = int(data.get('clip_min', 200))
            clip_max = int(data.get('clip_max', 10000))
            silence_time = int(data.get('silence_time', 400))
            
            sensitivity = int(data.get('sensitivity', 3))
            # info(">>> sensitivity")
            # info(sensitivity)
            
            self.client_id = data.get('client_id', "")
            # info(">>> client_id")
            # info(self.client_id) 

            # Webhook URL for analytics (optional for client app)
            self.webhook_url = data.get('webhook_url', "")
            # info(">>> webhook_url")
            # info(self.webhook_url)
    
            self.vad.set_mode(sensitivity)
            self.silence = silence_time // MS_PER_FRAME
            self.processor = LexProcessor(
                self.path, self.rate, clip_min, region, data['aws_key'], data['aws_secret'], self.client_id, self.webhook_url).process
            self.frame_buffer = BufferedPipe(
                clip_max // MS_PER_FRAME, self.processor)
            self.write_message('ok')

    def on_close(self):
        # Remove the connection from the list of connections
        del conns[self.id]
        info("client disconnected")


class PingHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def get(self):
        self.write('ok')
        self.set_header("Content-Type", 'text/plain')
        self.finish()

def main(argv=sys.argv[1:]):
    try:
        ap = argparse.ArgumentParser()
        ap.add_argument("-v", "--verbose", action="count")
        args = ap.parse_args(argv)
        logging.basicConfig(
            level=logging.DEBUG if args.verbose != None else logging.INFO,
            format="%(levelname)7s %(message)s",
        )
        print("Logging level is {}".format(logging.getLevelName(logging.getLogger().level)))
        application = tornado.web.Application([
            url(r"/ping", PingHandler),
            url(r"/(.*)", WSHandler),
        ])
        http_server = tornado.httpserver.HTTPServer(application)
        http_server.listen(PORT)
        info("Running on port %s", PORT)
        tornado.ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        pass  # Suppress the stack-trace on quit


if __name__ == "__main__":
    main()
