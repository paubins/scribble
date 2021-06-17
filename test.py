p="AccountSid=AC20a885d43487df76d014cab7934bf7aa&ApiVersion=2010-04-01&ApplicationSid=AP70b679465952b6f759ae9f3915a2f48e&CallSid=CA9f19a72e22127a865f0250e08b7a7119&CallStatus=completed&Called=%2B17377274225&CalledCity=&CalledCountry=US&CalledState=TX&CalledZip=&Caller=%2B17082785155&CallerCity=SCHAUMBURG&CallerCountry=US&CallerState=IL&CallerZip=60194&Digits=hangup&Direction=inbound&From=%2B17082785155&FromCity=SCHAUMBURG&FromCountry=US&FromState=IL&FromZip=60194&RecordingDuration=12&RecordingSid=RE731463d405b4bfa87e085801ca49c083&RecordingUrl=https%3A%2F%2Fapi.twilio.com%2F2010-04-01%2FAccounts%2FAC20a885d43487df76d014cab7934bf7aa%2FRecordings%2FRE731463d405b4bfa87e085801ca49c083&To=%2B17377274225&ToCity=&ToCountry=US&ToState=TX&ToZip="


from urllib.parse import unquote, parse_qsl
# print(parse_qs(p))


print(dict(parse_qsl(p)))