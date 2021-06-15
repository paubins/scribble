import boto3
import urllib.parse
from botocore.vendored import requests
import os
import json
from twilio.rest import Client

import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

API_KEY=os.environ["API_KEY"] #3f6_KDAKE1MgRd5jXKaW-fDim-s"
USER_KEY=os.environ["USER_KEY"] #XhgAAN/gXxd55+fVf6Vy0BUfRRc="
REV_URL=os.environ["REV_URL"] #https://api-sandbox.rev.com"
WEBHOOK=os.environ["WEBHOOK"]
ACCOUNT_SID = os.environ['TWILIO_ACCOUNT_SID']
AUTH_TOKEN = os.environ['TWILIO_AUTH_TOKEN']

def lambda_handler(event, context):
    client = Client(ACCOUNT_SID, AUTH_TOKEN)
    try:
        # Rev callback
        print(event)
        order_number = event["order_number"]
        client_ref = event["client_ref"]
        print(REV_URL)
        REV_ORDER_URL = os.path.join(REV_URL, f"api/v1/orders/{order_number}")
        print(REV_ORDER_URL)
        order_response = requests.get(REV_ORDER_URL, headers={
            "Authorization": f"Rev {API_KEY}:{USER_KEY}",
            "Content-Type": "application/json"
        })

        print(order_response.content)
        print(urllib.parse.unquote(client_ref))
        response = json.loads(order_response.content)
        from_num, to_num = urllib.parse.unquote(client_ref).split("-")

        attachment_id = [attachment["id"] for attachment in response["attachments"] if attachment["kind"] == "transcript"][0]
        print(attachment_id)

        attachment_response = requests.get(os.path.join(REV_URL, f"api/v1/attachments/{attachment_id}/content.txt"), headers={
            "Authorization": f"Rev {API_KEY}:{USER_KEY}"
        })
        call_content = attachment_response.content.decode('utf-8')
        print(call_content)
        message = client.messages \
                .create(
                     body=call_content,
                     from_=urllib.parse.unquote(from_num),
                     to=urllib.parse.unquote(to_num)
                 )

        print(message.sid)
    except Exception as e:
        print(e)
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

        from_num = event["Called"]
        to_num = event["From"]

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
                },
                "client_ref" : f"{from_num}-{to_num}"
            }))

        message = client.messages \
                        .create(
                             body="Your phone note is currently being processed, should take about 5 minutes.",
                             from_=urllib.parse.unquote(event["Called"]),
                             to=urllib.parse.unquote(event["From"]),
                             media_url=[audio_url + ".mp3"]
                         )

        print(message.sid)

    print(response)
    return '<?xml version=\"1.0\" encoding=\"UTF-8\"?>'\
           '<Response><Message><Body>it worked</Body></Message></Response>'
