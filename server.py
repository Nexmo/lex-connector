#!/usr/bin/env python

from __future__ import absolute_import, print_function

import argparse
import ConfigParser as configparser
import io
import logging
import os
import sys
import time
from ConfigParser import SafeConfigParser as ConfigParser
from logging import debug, info

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

CLIP_MIN_MS = 500  # 500ms - the minimum audio clip that will be used
MAX_LENGTH = 10000  # Max length of a sound clip for processing in ms
SILENCE = 20  # How many continuous frames of silence determine the end of a phrase

# Constants:
BYTES_PER_FRAME = 640  # Bytes in a frame
MS_PER_FRAME = 20  # Duration of a frame in ms

CLIP_MIN_FRAMES = CLIP_MIN_MS // MS_PER_FRAME

# Global variables
conns = {}

DEFAULT_CONFIG = """
[lexmo]
"""




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

    def append(self, data, cli):
        """ Add another data to the buffer. `data` should be a `bytes` object. """

        self.count += 1
        self.payload += data

        if self.count == self.max_frames:
            self.process(cli)

    def process(self, cli):
        """ Process and clear the buffer. """
        self.sink(self.count, self.payload, cli)
        self.count = 0
        self.payload = b''


class LexProcessor(object):
    def __init__(self, path, aws_id, aws_secret):
        self._aws_region = 'us-east-1'
        self._aws_id = aws_id
        self._aws_secret = aws_secret
        self._path = path
    def process(self, count, payload, cli):
        if count > CLIP_MIN_FRAMES:  # If the buffer is less than CLIP_MIN_MS, ignore it
            auth = AWS4Auth(self._aws_id, self._aws_secret, 'us-east-1', 'lex')
            info('Processing {} frames from {}'.format(str(count), cli))
            endpoint = 'https://runtime.lex.{}.amazonaws.com{}'.format(self._aws_region, self._path)
            headers = {'Content-Type': 'audio/l16; channels=1; rate=16000', 'Accept': 'audio/pcm'}
            req = requests.Request('POST', endpoint, auth=auth, headers=headers)
            prepped = req.prepare()
            r = requests.post(endpoint, data=payload, headers=prepped.headers)
            info(r.headers)
            self.playback(r.content, cli)
        else:
            info('Discarding {} frames'.format(str(count)))
    def playback(self, content, cli):
        frames = len(content) // 640
        info("Playing {} frames to {}".format(frames, cli))
        conn = conns[cli]
        pos = 0
        for x in range(0, frames + 1):
            newpos = pos + 640
            debug("writing bytes {} to {} to socket for {}".format(pos, newpos, cli))
            data = content[pos:newpos]
            conn.write_message(data, binary=True)
            time.sleep(0.018)
            pos = newpos



class WSHandler(tornado.websocket.WebSocketHandler):
    def initialize(self):
        # Create a buffer which will call `process` when it is full:
        self.frame_buffer = None
        # Setup the Voice Activity Detector
        self.tick = None
        self.cli = None
        self.vad = webrtcvad.Vad()
        self.vad.set_mode(1)  # Level of sensitivity
        self.processor = None
        self.path = None
    def open(self, path):
        info("client connected")
        debug(self.request.uri)
        self.path = self.request.uri
        self.tick = 0
    def on_message(self, message):
        # Check if message is Binary or Text
        if type(message) == str:
            if self.vad.is_speech(message, 16000):
                debug ("SPEECH from {}".format(self.cli))
                self.tick = SILENCE
                self.frame_buffer.append(message, self.cli)
            else:
                debug("Silence from {} TICK: {}".format(self.cli, self.tick))
                self.tick -= 1
                if self.tick == 0:
                    self.frame_buffer.process(self.cli)  # Force processing and clearing of the buffer
        else:
            info(message)
            # Here we should be extracting the meta data that was sent and attaching it to the connection object
            data = json.loads(message)
            self.cli = data['cli']
            conns[self.cli] = self
            self.processor = LexProcessor(self.path, data['aws_key'], data['aws_secret']).process
            self.frame_buffer = BufferedPipe(MAX_LENGTH // MS_PER_FRAME, self.processor)
            self.write_message('ok')
    def on_close(self):
        # Remove the connection from the list of connections
        del conns[self.cli]
        info("client disconnected")



class Config(object):
    def __init__(self, specified_config_path):
        config = ConfigParser()
        config.readfp(io.BytesIO(DEFAULT_CONFIG))
        config.read("./lexmo.conf")
        # Validate config:
        try:
            self.host = os.getenv('HOST') or config.get("lexmo", "host")
            self.port = os.getenv('PORT') or config.getint("lexmo", "port")
        except configparser.Error as e:
            print("Configuration Error:", e, file=sys.stderr)
            sys.exit(1)


def main(argv=sys.argv[1:]):
    try:
        ap = argparse.ArgumentParser()
        ap.add_argument("-v", "--verbose", action="count")
        ap.add_argument("-c", "--config", default=None)
        args = ap.parse_args(argv)
        logging.basicConfig(
            level=logging.INFO if args.verbose < 1 else logging.DEBUG,
            format="%(levelname)7s %(message)s",
        )
        config = Config(args.config)
        application = tornado.web.Application([
            url(r"/(.*)", WSHandler),
        ])
        http_server = tornado.httpserver.HTTPServer(application)
        http_server.listen(config.port)
        info("Running on port %s", config.port)
        tornado.ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        pass  # Suppress the stack-trace on quit


if __name__ == "__main__":
    main()
