# Lex Connector

You can use the Lex connector to connect a Nexmo voice call to a Lex bot and then talk to the bot via audio.

The connector makes use of the  websockets feature of the Nexmo Voice API, when a call is established the API then makes a websocket connection to the connector and streams the audio to and from the call in real time. 
The connector then takes care of captuing chunks of speach using Voice Activity Detection to then post to the Lex Endpoint, when Lex returns audio the Connector then streams that back over the webscoket to the call.

The connector does not store any Lex specific configuration or credentials you supply those within the NCCO telling the Voice API to connect the call to the Connector, This is a standard connect function with a few specific parameters:

Here is an example of the NCCO you should return for your incomming calls:
```
[
{
	"action": "talk",
	"text": "Hello, I am Lex, how can I help you"
}, 
{
	"action": "connect",
	"eventUrl": ["http://example.com/event"],
	"endpoint": [{
		"type": "websocket",
		"uri": "ws://lex.nexmo.com/bot/BOTNAME/alias/ALAIS/user/USER/content",
		"content-type": "audio/l16;rate=16000",
		"headers": {
			"cli": "447790900123",
			"aws_key": "AAAAAAAAAAAAAAAAAAAAAAAAAAA",
			"aws_secret": "eescOz9xisx+gx-PFU3G4AJg4NE4UExnHYaijI+o6xgNT0"
		}
	}]
}
]
```
The first `talk` action is a simple way to start the call, as Lex expects the first speech to come from the user we need to start off the conversation as in a phone call users expect the "person" that answers to say something. You can customise this text to fit your use case, Also you should look at the range of voices avalible on Nexmo and Lex and select the same voice so that it feels the most naturual. Nexmo have many of the same voices as Lex.

The next action is the `connect`, this is telling the call to be connected to a websocket endpoint, in this case the endpoint is our Lex Connector.

The path portion of te uri is the same as the path to the PostContent endpoint within Lex [http://docs.aws.amazon.com/lex/latest/dg/API_PostContent.html] but with the `lex.nexmo.com`  host instead of AWS. Therefore you shoud set your BOTNAME, ALIAS and USER details as part of this URI

Within the headers section of the endpoint you must supply the `aws_key` and `aws_secret` that will be used to connect to Lex. You should also specify the caller ID as a `cli` parameter here.

The `eventUrl` is where Nexmo will send events regarding the connection to the Lex Connector so that your application can be aware of the start and end of a session, currently we do not share any data or events on the requests to and from Lex.

The `content-type` is a fixed value.

