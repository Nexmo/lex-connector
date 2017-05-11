# Lex Connector

You can use the Lex Connector to connect a Nexmo voice call to a Lex bot and then have an audio conversation with the bot.

Lex Connector makes use of the [WebSockets feature](https://docs.nexmo.com/voice/voice-api/websockets) of Nexmo's Voice API. When a call is established, the API makes a websocket connection to Lex Connector and streams the audio to and from the call in real time.

Lex Connector then takes care of capturing chunks of speach using Voice Activity Detection to then post to the Lex Endpoint. When Lex returns audio, Lex Connector streams that back over the websocket to the call.

Lex Connector does not store any Lex-specific configuration or credentials: these are supplied in the NCCO, telling the Voice API to connect the call to the Connector. This is a standard `connect` function used to connect calls to WebSockets, with a few specific parameters to connect to Lex.

Here is an example of the NCCO you should return to handle incoming calls:

```
[
    {
        "action": "talk",
        "text": "Hello, I am Lex, how can I help you?"
    },
    {
        "action": "connect",
        "endpoint": [
            {
                "content-type": "audio/l16;rate=16000",
                "headers": {
                    "aws_key": "AAAAAAAAAAAAAAAAAAAAAAAAAAA",
                    "aws_secret": "eescOz9xisx+gx-PFU3G4AJg4NE4UExnHYaijI+o6xgNT0"
                },
                "type": "websocket",
                "uri": "wss://lex-us-east-1.nexmo.com/bot/BOTNAME/alias/ALAIS/user/USER/content"
            }
        ],
        "eventUrl": [
            "http://example.com/event"
        ]
    }
]
```

The first `talk` action is a simple way to start the call: Lex expects the user to speak first, so we need to start the conversation as one would in a phone call, with the answerer greeting the caller. You can customise this text to fit your use case.

You should look at the [range of voices available on Nexmo](https://docs.nexmo.com/voice/voice-api/ncco-reference#talk) and on Lex to select the same voice, so that it feels natural for the caller. (There is some overlap in the choice of voices available from both Nexmo and Lex.)

The next action is `connect`: this makes call connect to the WebSocket endpoint, specifically the Lex Connector WebSocket.

The path portion of the uri is the same as the path to the `PostContent` endpoint within Lex [http://docs.aws.amazon.com/lex/latest/dg/API_PostContent.html] but with the `lex-us-east-1.nexmo.com` as host instead of AWS. Therefore you should set your BOTNAME, ALIAS and USER details as part of this URI. You can get these details from the AWS Console.

Within the headers section of the endpoint you must supply the `aws_key` and `aws_secret` that will be used to connect to Lex.

The `eventUrl` is where Nexmo will send events regarding the connection to the Lex Connector so that your application can be aware of the start and end of a session. Currently we do not share any data or events on the requests to and from Lex: the events sent are simply the start and end of the call.

The `content-type` is a fixed value.

## Running LexConnector

You want to run your own instance of LexConnector? There should be no need to run your own server normally, as we host a public version on `lex-us-east-1.nexmo.com`. If you *do* want to run your own instance, you'll need an up-to-date version of Python 2. Install dependencies with:

```bash
pip install --upgrade -r requirements.txt
```

Copy the `lexmo.conf.template` file to `lexmo.conf` and modify it with the hostname and port you wish to use to host the service. The port is internal to you - LexConnector assumes the service can be accessed via port 80 on the hostname you provide, with something like NGinx proxying to the port you've provided. LexConnector is a WebSocket based service, so make sure your proxy is configured to handle WebSocket connections! If you don't wish to run a proxy in front of LexConnector, just set the port to 80.

Run the server like this:

```bash
python server.py --config lexmo.conf
```

Obviously the WebSocket URL you use in your NCCO should use the hostname of your service, instead of `lex-us-east-1.nexmo.com`.

## Credits

* Mark Smith, [@judy2k](https://twitter.com/judy2k)
