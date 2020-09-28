# Lex Connector

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](http://nexmo.dev/lex-connector-heroku)

You can use the Lex Connector to connect a Vonage Voice API call to a Lex bot and then have an audio conversation with the bot.

## Amazon Lex

In order to get started, you will need to have a [AWS account](http://aws.amazon.com), as well as a bot on [Amazon Lex](https://aws.amazon.com/lex/).
After your bot is configured, you will need to obtain your AWS key and secret.

To find your Access Key and Secret Access Key:

- Log in to your [AWS Management Console](http://aws.amazon.com).
- Click on your user name at the top right of the page.
- Click on the Security Credentials link from the drop-down menu.
- Find the Access Credentials section, and copy the latest Access Key ID.
- Click on the Show link in the same row, and copy the Secret Access Key.

You will also need your bot name, which can be found in the Settings -> General on your Amazon Lex bot page, as well as the Alias of the bot, which is located in Settings -> Alias.

## About The Lex Connector

Lex Connector makes use of the [WebSockets feature](https://docs.nexmo.com/voice/voice-api/websockets) of Nexmo's Voice API. When a call is established, the API makes a websocket connection to Lex Connector and streams the audio to and from the call in real time.

Lex Connector then takes care of capturing chunks of speech using Voice Activity Detection to then post to the Lex Endpoint. When Lex returns audio, Lex Connector streams that back over the websocket to the call.

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
                "content-type": "audio/l16;rate=8000",
                "headers": {
                    "aws_key": "AAAAAAAAAAAAAAAAAAAAAAAAAAA",
                    "aws_secret": "eescOz9xisx+gx-PFU3G4AJg4NE4UExnHYaijI+o6xgNT0",
                    "sensitivity": 3
                },
                "type": "websocket",
                "uri": "wss://xxxxx.ngrok.io/bot/BOTNAME/alias/ALIAS/user/USER/content"
            }
        ],
        "eventUrl": [
            "http://example.com/event"
        ]
    }
]
```

The connector provides a handler on `/answer` which will serve the contents of `example_ncco.json` to faclitate testing.

The first `talk` action is a simple way to start the call: Lex expects the user to speak first, so we need to start the conversation as one would in a phone call, with the answerer greeting the caller. You can customise this text to fit your use case.

You should look at the [range of voices available on Nexmo](https://docs.nexmo.com/voice/voice-api/ncco-reference#talk) and on Lex to select the same voice, so that it feels natural for the caller. (There is some overlap in the choice of voices available from both Nexmo and Lex.)

The next action is `connect`: this makes the call connect to the WebSocket endpoint, specifically the Lex Connector WebSocket.

The parameter `sensitivity` allows you to set the VAD (Voice Activity Detection) sensitivity from the most sensitive (value = 0) to the least sensitive (value = 3), this is an integer value.

The path portion of the uri is the same as the path to the `PostContent` [endpoint within Lex](http://docs.aws.amazon.com/lex/latest/dg/API_PostContent.html) but with your server host address, e.g. `xxxxx.ngrok.io`. Therefore you should set your BOTNAME, ALIAS and USER details as part of this URI. You can get these details from your AWS Console after you set up a new instance of Lex.

Within the headers section of the endpoint you must supply your `aws_key` and `aws_secret` that will be used to connect to Lex.

The `eventUrl` is where Nexmo will send events regarding the connection to the Lex Connector so that your application can be aware of the start and end of a session. Currently we do not share any data or events on the requests to and from Lex. The only events sent to this URL are about the start and end of the call.


## Running LexConnector

If you wish to deploy your own version of the Lex Connector you can do so in the following ways.

### Docker

Start by copying the `.env.example` file over to a new file called `.env`:

```bash
cp .env.example > .env
```

Modify the contents of the file to include your own `HOSTNAME` and `PORT`. You can then launch the Lex Connector as a Docker instance by running:

```bash
docker-compose up
```

### Heroku

You can deploy this application to Heroku in a single click using the 'Deploy to Heroku' button at the top of this page. Or directly from the command line using the Heroku CLI:

```bash
heroku create
```

Then deploy the app:

```bash
git push heroku master
```

Once the app is deployed, make a note of the URL as this is what you will need to change your websocket URI to in your NCCO in order to connect the call to the Lex Connector.

### Local Install


To run your own instance locally you'll need an up-to-date version of Python 3. Install dependencies with:

```bash
pip install --upgrade -r requirements.txt
```

Copy the `.env` example over to a new file and replace the contents with your own `HOSTNAME` and `PORT`

```bash
cp .env.example > .env
```

The port is internal to you - LexConnector assumes the service can be accessed via the default port (80/443) on the hostname you provide, with something like NGinx proxying to the port you've provided.

LexConnector is a WebSocket based service, so make sure your proxy is configured to handle WebSocket connections if you have one.

If you don't wish to run a proxy in front of LexConnector, just set the port to 80.

### Running the example

Run the server like this:

```bash
python server.py
```

The WebSocket URL you use in your NCCO should use the hostname of your service wherever it is running, and if you don't have SSL set up, you'll need to change the `wss` prefix to `ws`.
