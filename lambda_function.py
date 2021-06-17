import boto3
import urllib.parse
from botocore.vendored import requests
import os
import json
from twilio.rest import Client

from sgqlc.operation import Operation
from sgqlc.endpoint.http import HTTPEndpoint

from onesignal_sdk.client import Client as OneSignalClient

import hmac
import hashlib
import requests

from urllib.parse import unquote, parse_qsl
import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

API_KEY=os.environ.get("API_KEY", "") #3f6_KDAKE1MgRd5jXKaW-fDim-s"
USER_KEY=os.environ.get("USER_KEY", "") #XhgAAN/gXxd55+fVf6Vy0BUfRRc="
REV_URL=os.environ.get("REV_URL", "") #https://api-sandbox.rev.com"
WEBHOOK=os.environ.get("WEBHOOK", "")

ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
VERIFY_SERVICE_SID = os.environ.get("VERIFY_SERVICE_SID", "")

ONESIGNAL_APP_ID = os.environ.get("ONESIGNAL_APP_ID", "")
ONESIGNAL_REST_API_KEY = os.environ.get("ONESIGNAL_REST_API_KEY", "")
ONESIGNAL_USER_AUTH_KEY = os.environ.get("ONESIGNAL_USER_AUTH_KEY", "")

GRAPHCMS_TOKEN = os.environ.get("GCMS_TOKEN", "")
GRAPHCMS_ENDPOINT = os.environ.get('GRAPHCMS_ENDPOINT', "")


def lambda_handler(event, context):
    client = Client(ACCOUNT_SID, AUTH_TOKEN)
    print(event)
    print(context)

    query = dict(parse_qsl(event['body-json']))
    path = event['context']['resource-path']

    if "start" in path:
        country_code = query.get("country_code")
        phone_number = query.get("phone_number")
        full_phone = "+{}{}".format(country_code, phone_number)

        try:
            r = client.verify \
                .services(VERIFY_SERVICE_SID) \
                .verifications \
                .create(to=full_phone, channel='sms')
            return json.dumps({"success" : True, "message" : "Verification sent to {}".format(r.to)})
        except Exception as e:
            return json.dumps({"success" : False, "message" : "Error sending verification: {}".format(e)})
    elif "check" in path:
        country_code = query.get("country_code")
        phone_number = query.get("phone_number")
        full_phone = "+{}{}".format(country_code, phone_number)
        code = query.get("verification_code")
        device_id = query.get("device_id")

        try:
            r = client.verify \
                .services(VERIFY_SERVICE_SID) \
                .verification_checks \
                .create(to=full_phone, code=code)

            if r.status == "approved":
                # insert into graph db
                print(full_phone)
                signature = hmac.new(ONESIGNAL_REST_API_KEY, full_phone, hashlib.sha256).hexdigest()
                q3 = """
                    mutation {
                      upsertContact(
                        where: { phone: "%s" }
                        upsert: {
                          create: { phone: "%s", device_id: "%s" }
                          update: { phone: "%s", device_id: "%s" }
                        }
                      ) {
                        id
                        phone
                      }
                    }
                    """ % (signature)
                result = endpoint(query=q3)
                print(result)
                return json.dumps({"success" : True, "message" : "Valid token."})
            else:
                return json.dumps({"success" : False, "message" : "Invalid token."})
        except Exception as e:
            return json.dumps({"success" : False, "message" : "Error checking verification: {}".format(e)})

    try:
        # Rev callback
        print(query)
        order_number = query["order_number"]
        client_ref = query["client_ref"]
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

        # grab the associated device id
        headers = {'Authorization': f"Bearer {GRAPHCMS_TOKEN}"}
        endpoint = HTTPEndpoint(GRAPHCMS_ENDPOINT, headers)
        print(from_num)

        signature = hmac.new(ONESIGNAL_REST_API_KEY, from_num, hashlib.sha256).hexdigest()

        q3 = """
            query {
              contact(where: {phone: "%s"}) {
                device_id
              }
            }
            """ % (signature)
        result = endpoint(query=q3)
        print(result)

        try:
            device_id = result['data']['contact']['device_id']
            print(device_id)

            os_client = OneSignalClient(app_id=ONESIGNAL_APP_ID,
                rest_api_key=ONESIGNAL_REST_API_KEY,
                user_auth_key=ONESIGNAL_USER_AUTH_KEY)

            try:
                notification_body = {
                    'contents': {'en': 'New notification'},
                    'included_segments': [device_id],
                }

                # Make a request to OneSignal and parse response
                response2 = os_client.send_notification(notification_body)
                print(response2.body) # JSON parsed response
                print(response2.status_code) # Status code of response
                print(response2.http_response) # Original http response object.

            except OneSignalHTTPError as e: # An exception is raised if response.status_code != 2xx
                print(e)
                print(e.status_code)
                print(e.http_response.json())

        except Exception as e:
            print(e)

        print(response.body)

    except Exception as e:
        print(e)
        # Twilio callback
        audio_length=query["RecordingDuration"]
        audio_url=urllib.parse.unquote(query["RecordingUrl"])
        
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

        from_num = query["Called"]
        to_num = query["From"]

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
                             from_=urllib.parse.unquote(query["Called"]),
                             to=urllib.parse.unquote(query["From"]),
                             media_url=[audio_url + ".mp3"]
                         )

        print(message.sid)

    print(response)
    return '<?xml version=\"1.0\" encoding=\"UTF-8\"?>'\
           '<Response><Message><Body>it worked</Body></Message></Response>'
