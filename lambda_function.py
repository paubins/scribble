import boto3
import urllib.parse
from botocore.vendored import requests
import os
import json
from twilio.rest import Client

API_KEY=os.environ["API_KEY"] #3f6_KDAKE1MgRd5jXKaW-fDim-s"
USER_KEY=os.environ["USER_KEY"] #XhgAAN/gXxd55+fVf6Vy0BUfRRc="
REV_URL=os.environ["REV_URL"] #https://api-sandbox.rev.com"
WEBHOOK=os.environ["WEBHOOK"]
account_sid = os.environ['TWILIO_ACCOUNT_SID']
auth_token = os.environ['TWILIO_AUTH_TOKEN']

def lambda_handler(event, context):
    try:
        # Rev callback
        order_number = event["order_number"]
        REV_ORDER_URL = os.path.join(REV_URL, f"orders/{order_number}")
        
        order_response = requests.get(REV_ORDER_URL, headers={
            "Authorization": f"Rev {API_KEY}:{USER_KEY}",
            "Content-Type": "application/json"
        })
        
        attachment_id = [attachment["id"] for attachment in response["attachments"] if attachment["kind"] == "transcript"][0]
        attachment_response = requests.get(os.path.join(REV_URL, f"attachments/{attachment_id}/content"), headers={
            "Authorization": f"Rev {API_KEY}:{USER_KEY}"
        })
        print(attachment_response.content)
        
        sns = boto3.client('sns')
        sns.publish(
            TopicArn = "arn:aws:sns:us-east-1:497284921492:jott-another",
            Message = attachment_response.content
        )
    except:
        # Twilio callback
        audio_length=event["RecordingDuration"]
        audio_url=urllib.parse.unquote(event["RecordingUrl"])
        
        print("upload the file and the uri")
        file_uri = requests.post(os.path.join(REV_URL, "api/v1/inputs"), headers={
                "Authorization": f"Rev {API_KEY}:{USER_KEY}",
                "Content-Type": "application/json"
            }, data=json.dumps({"content_type": "audio/x-wav", "url": audio_url}))
            
        print(file_uri.content)
        print(file_uri.headers)
        file_uri = file_uri.headers["Location"]
        
        print(f"submit order with input {file_uri}")
        print(os.path.join(REV_URL, "api/v1/orders"))
        response = requests.post(os.path.join(REV_URL, "api/v1/orders"), headers={
                "Authorization": f"Rev {API_KEY}:{USER_KEY}",
                "Content-Type": "application/json"
            }, data=json.dumps({
                "transcription_options": {
                    "inputs": [
                        {
                            "audio_length_seconds": audio_length,
                            "uri": file_uri
                        }
                    ],
                    "verbatim": True,
                    "timestamps": False,
                    "rush": True,
                    "instant_first_draft": False,
                    "output_file_formats": ["Text"]
                },
                "notification": {
                    "url": WEBHOOK,
                    "level": "FinalOnly"
                }
            }))

        client = Client(account_sid, auth_token)

        message = client.messages \
                        .create(
                             body="Join Earth's mightiest heroes. Like Kevin Bacon.",
                             from_='+18167354511',
                             to='+17082785155'
                         )

        print(message.sid)

    print(response)
    return '<?xml version=\"1.0\" encoding=\"UTF-8\"?>'\
           '<Response><Message><Body>it worked</Body></Message></Response>'
