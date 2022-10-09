import csv
import requests
from config import *

from datetime import datetime, timedelta
# Switched to pycognito because Warrant won't build anymore
from pycognito import Cognito

bot = ""

u = Cognito(
    COGNITO_POOL_ID, 
    COGNITO_CLIENT_ID,
    username=AWS_EVENTS_USERNAME 
)
u.authenticate(password=AWS_EVENTS_PASSWORD)

# Seems to be the same for the past couple years...
url = "https://api.us-east-1.prod.events.aws.a2z.com/attendee/graphql"

# Authentication token for accessing the GraphQL endpoint
headers = {
    "Authorization": "Bearer " + u.access_token,
}
print("Access Token:")
# print(u.access_token)

# GraphQL query, 100 at a time, for AWS re:Invent sessions
# One can modify the "query" by hitting F12 to trigger development tools while logged into AWS Events and finding the ListSessions text in one of the .js files... 
#   From there you can see the complete schema available and tease out whatever additional details are needed
# Can get the current eventId from F12 to trigger development tools while logged into AWS Events and finding a "query" in 
body = {
    "operationName": "ListSessions",
    "variables": {
        "input": {
            "eventId": "53b5de8d-7b9d-4fcc-a178-6433641075fe", 
            "maxResults": 100,
        }
    },
    "query": "query ListSessions($input: ListSessionsInput!) {\n  listSessions(input: $input) {\n    results {\n      ...SessionFieldFragment\n      isConflicting {\n        reserved {\n          eventId\n          sessionId\n          isPaidSession\n          __typename\n        }\n        waitlisted {\n          eventId\n          sessionId\n          isPaidSession\n          __typename\n        }\n        __typename\n      }\n      __typename\n    }\n    totalCount\n    nextToken\n    __typename\n  }\n}\n\nfragment SessionFieldFragment on Session {\n  action\n  alias\n  createdAt\n  description\n  duration\n  endTime\n  eventId\n  isConflicting {\n    reserved {\n      alias\n      createdAt\n      eventId\n      name\n      sessionId\n      type\n      __typename\n    }\n    waitlisted {\n      alias\n      createdAt\n      eventId\n      name\n      sessionId\n      type\n      __typename\n    }\n    __typename\n  }\n  isEmbargoed\n  isFavoritedByMe\n  isPaidSession\n  isPaidSession\n  level\n  location\n  myReservationStatus\n  name\n  sessionId\n  startTime\n  status\n  type\n  capacities {\n    reservableRemaining\n    waitlistRemaining\n    __typename\n  }\n  customFieldDetails {\n    name\n    type\n    visibility\n    fieldId\n    ... on CustomFieldValueFlag {\n      enabled\n      __typename\n    }\n    ... on CustomFieldValueSingleSelect {\n      value {\n        fieldOptionId\n        name\n        __typename\n      }\n      __typename\n    }\n    ... on CustomFieldValueMultiSelect {\n      values {\n        fieldOptionId\n        name\n        __typename\n      }\n      __typename\n    }\n    ... on CustomFieldValueHyperlink {\n      text\n      url\n      __typename\n    }\n    __typename\n  }\n  package {\n    itemId\n    __typename\n  }\n  price {\n    currency\n    value\n    __typename\n  }\n  room {\n    name\n    venue {\n      name\n      __typename\n    }\n    __typename\n  }\n  sessionType {\n    name\n    __typename\n  }\n  tracks {\n    name\n    __typename\n  }\n  speakers {\n  jobTitle\n  companyName\n   user {\n    firstName\n lastName\n    __typename\n  }\n  __typename\n  }\n  __typename\n}\n"
}

next_token = True
sessions = []

# Loop through each set of 100 sessions
while next_token:
    print("Getting sessions...")
    response = requests.post(
        url,
        headers=headers,
        json=body,
    )
    response_data = response.json()

    print("    Total Returned:", len(response_data["data"]["listSessions"]["results"]))
    sessions = sessions + response_data["data"]["listSessions"]["results"]

    if "nextToken" in response_data["data"]["listSessions"] and response_data["data"]["listSessions"]["nextToken"] is not None:
        next_token = True
        #print("    Next Token:", response_data["data"]["listSessions"]["nextToken"])
        body["variables"]["input"]["nextToken"] = response_data["data"]["listSessions"]["nextToken"]
    else:
        next_token = False
    # next_token = False # for testing of one iteration


# Open a blank text file to write sessions to
sessions_file = open("sessions.csv","w")
sessions_writer = csv.writer(sessions_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
sessions_writer.writerow([
    "Session Number", 
    "Session Title", 
    "Session Interest", 
    "Start Time", 
    "End Time", 
    "Room and Building",
    "Venue",
    "Description",
    "Level",
    "Type",
    "Speaker Company",
    "Tracks"
    ])

# Iterate thru sessions writing to file
for session in sessions:
    session_number = session["alias"]
    session_name = session["name"]
    session_description = session["description"].encode("utf-8") if session['description'] is not None else "n/a"
    session_level = session["level"]  if session['level'] is not None else "n/a"
    session_type = session['sessionType']['name']  if session['sessionType'] is not None else "n/a"
    session_speaker_company = ""

    if "speakers" in session and session['speakers'] is not None:
        for speaker in session['speakers']:
            for key, value in speaker.items():
                if key == "companyName":
                    session_speaker_company = session_speaker_company + value + ","
    else:
       session_speaker_company = "n/a"

    session_tracks = "" #session["tracks"]["name"]  if session["tracks"] is not None else "n/a"

    #print("Session Name: " + session_name)
    venue_name = session['room']['venue']['name'] if session['room'] is not None and session['room']['venue'] is not None else "n/a"
    room_name = session['room']['name'] if session['room'] is not None and session['room']['name'] is not None else "n/a"
    room_building = f"{venue_name} - {room_name}"
    
    if session["startTime"] is not None:
        start_time = datetime.fromtimestamp(session["startTime"]/1000)
        end_time = start_time + timedelta(minutes=session["duration"])
        start_time = start_time.strftime("%x %X")
        end_time = end_time.strftime("%x %X")
    else:
        start_time = "0"
        end_time = "0"

    session_info = {
        "session_number": session_number,
        "session_title": session_name,
        "start_time": start_time,
        "end_time": end_time,
        "room_building": room_building,
        "venue": venue_name,
        "session_description": session_description,
        "session_level": session_level,
        "session_type": session_type,
        "session_speaker_company": session_speaker_company,
        "session_tracks": session_tracks
    }

    if (session["isFavoritedByMe"] == False):
        session_interest = False
    else:
        session_interest = True

    sessions_writer.writerow([
        session_number, 
        session_name, 
        session_interest, 
        start_time, 
        end_time, 
        room_building,
        venue_name,
        session_description,
        session_level,
        session_type,
        session_speaker_company,
        session_tracks
    ])

# Close out file for use
sessions_file.close()
