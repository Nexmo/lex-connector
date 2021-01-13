# Lex Connector

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/Nexmo/lex-connector/heroku)

You can use the Lex Connector to connect a Vonage Voice API call to a Lex bot and then have an audio conversation with the bot. Voice transcripts and sentiment analysis are posted back to the Vonage Voice API application.

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

Lex Connector does not store any Lex-specific configuration or credentials: these are supplied in the NCCO from the Voice API application, telling the Voice API to connect the call to this Lex Connector. This is a standard `connect` function used to connect calls to WebSockets, with a few specific parameters to connect to Lex.

See https://github.com/nexmo-community/lex-client for a sample Voice API application using this connector to connect voice calls to an Amazon Lex Bot.

## Transcripts

This connector will send caller's transcript (labeled as customer) and Lex bot's transcript to the Voice API application via a webhook call.

## Sentiment analysis

You may enable sentiment analysis by going to AWS console, Amazon Lex, your Lex bot, then Settings/General.

This connector will send caller's sentiment analysis to the Voice API application via the same webhook call as mentioned above.

## Running Lex Connector

If you wish to deploy your own version of the Lex Connector you can do so in the following ways.

### Docker

Start by copying the `.env.example` file over to a new file called `.env`:

```bash
cp .env.example > .env
```

Edit `.env` file, set the `PORT` value where websockets connections will be established. You can then launch the Lex Connector as a Docker instance by running:

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

Copy the `.env.example` file over to a new file called `.env`.

```bash
cp .env.example > .env
```
Edit `.env` file, set the `PORT` value where websockets connections will be established.

The port is internal to you - LexConnector assumes the service can be accessed via the default port (80/443) on the hostname you provide, with something like NGinx proxying to the port you've provided.

LexConnector is a WebSocket based service, so make sure your proxy is configured to handle WebSocket connections if you have one.

If you don't wish to run a proxy in front of LexConnector, just set the port to 80.

### Running the example

Run the server like this:

```bash
python server.py
```

The WebSocket URL you use in your NCCO should use the hostname of your service wherever it is running, and if you don't have SSL set up, you'll need to change the `wss` prefix to `ws`.
