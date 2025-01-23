import os
import sys
import time

from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime
from datetime import datetime, timedelta





def gcal_auth():
    # Set up the Google Calendar API
    SCOPES = ['https://www.googleapis.com/auth/calendar']
    SERVICE_ACCOUNT_FILE = "py-android-scheduler_test.json"
    calId = "rootkalyan@gmail.com"
    # Authenticate using the service account credentials
    credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    # Build the Calendar service object
    service = build('calendar', 'v3', credentials=credentials)
    return service





# Get calendar information
# calendar = service.calendars().get(calendarId=calId).execute()
# print(f"Calendar Summary: {calendar['summary']}")

# Get upcoming 10 events
now = datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates U

def create_sample_eve(service,event_date):
    # Create an event
    start_time = datetime.strptime(f"{event_date} {datetime.now().time().strftime('%I:%M %p')}", '%Y-%m-%d %I:%M %p')
    calendar_id = "rootkalyan@gmail.com"

    end_time = datetime.strptime(f"{event_date} {datetime.now().time().strftime('%I:%M %p')}", '%Y-%m-%d %I:%M %p')+timedelta(hours=1)
    event_data = {
        'summary': "sample eve "+str(datetime.now().time()),
        'start': {
            'dateTime': start_time.isoformat(),
            'timeZone': 'America/Los_Angeles',  # Set to PST
        },
        'end': {
            'dateTime': end_time.isoformat(),
            'timeZone': 'America/Los_Angeles',  # Set to PST
        },
        'colorId': '3'  # Optional: set color for events
    }
    # # Call the Calendar API to insert the event
    try:
        event_result = service.events().insert(calendarId=calendar_id, body=event_data).execute()
        print(f"Event sample eve created successfully from {start_time} to {end_time}.")
    except Exception as e:
        print(f"Failed to create event sample eve: {e}")
    # event_result = service.events().insert(calendarId="rootkalyan@gmail.com", body=event_data).execute()
    # print(f"Event created: {event_result.get('htmlLink')}")



def get_todayeves(service,date):
    # Set up today's date range
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0).isoformat() + 'Z'
    today_end = datetime.utcnow().replace(hour=23, minute=59, second=59, microsecond=999999).isoformat() + 'Z'

    # Fetch all events for today's date
    events_result = service.events().list(calendarId=calId, timeMin=today_start, timeMax=today_end,
                                          maxResults=100, singleEvents=True,
                                          orderBy='startTime').execute()

    events = events_result.get('items', [])

    # Create a list of event details
    event_details = []

    if not events:
        print('No events found for today.')
    else:
        for event in events:
            event_data = {
                'id': event.get('id'),
                'summary': event.get('summary'),
                'start': event['start'].get('dateTime', event['start'].get('date')),
                'end': event['end'].get('dateTime', event['end'].get('date')),
                'description': event.get('description'),
                'location': event.get('location'),
                'attendees': event.get('attendees', [])
            }
            event_details.append(event_data)

    # Output event details
    for event in event_details:
        print(f"Event ID: {event['id']}, Summary: {event['summary']}, Start: {event['start']}, End: {event['end']}")




# sample items array :
items = [{'work': {'color': 'white', 'time': '8:00 AM', 'actual_done': ''}}, {'work': {'color': 'white', 'time': '9:00 AM', 'actual_done': ''}}, {'check use case sheet keep': {'color': 'white', 'time': '10:00 AM', 'actual_done': ''}}, {'work': {'color': 'white', 'time': '11:00 AM', 'actual_done': ''}}, {'work': {'color': 'white', 'time': '12:00 PM', 'actual_done': ''}}, {'work': {'color': 'white', 'time': '1:00 PM', 'actual_done': ''}}, {'lunch': {'color': 'white', 'time': '2:00 PM', 'actual_done': ''}}, {'visa related with ogs': {'color': 'white', 'time': '3:00 PM', 'actual_done': ''}}, {'h1b fragomen': {'color': 'white', 'time': '4:00 PM', 'actual_done': ''}}, {'': {'color': 'white', 'time': '5:00 PM', 'actual_done': ''}}, {'kids': {'color': 'white', 'time': '6:00 PM', 'actual_done': ''}}, {'pass': {'color': 'white', 'time': '7:00 PM', 'actual_done': ''}}, {'prep interview': {'color': 'white', 'time': '8:00 PM', 'actual_done': ''}}, {'dinner': {'color': 'white', 'time': '9:00 PM', 'actual_done': ''}}, {'prep interview': {'color': 'white', 'time': '10:00 PM', 'actual_done': ''}}, {'prep interview': {'color': 'white', 'time': '11:00 PM', 'actual_done': ''}}, {'prep interview': {'color': 'white', 'time': '2:00 AM', 'actual_done': ''}}, {'': {'color': 'white', 'time': '1:00 AM', 'actual_done': ''}}, {'': {'color': 'green', 'time': '2:00 AM', 'actual_done': ''}}, {'': {'color': 'white', 'time': '3:00 AM', 'actual_done': ''}}, {'': {'color': 'white', 'time': '', 'actual_done': ''}}, {'16': {'color': 'blue', 'time': 'Done', 'actual_done': ''}}, {'53': {'color': 'red', 'time': 'Not-done', 'actual_done': ''}}, {'16': {'color': 'white', 'time': 'unmarked', 'actual_done': ''}}, {'': {'color': 'white', 'time': '', 'actual_done': ''}}]


def create_events_from_items(service, items, event_date):
    # Adjusting the time zone to PST (UTC-8) without manually modifying the time
    service = gcal_auth()

    calendar_id = "rootkalyan@gmail.com"

    for item in items:
        for event_name, event_details in item.items():
            event_time = event_details['time']

            # Skip if time or event name is missing or invalid (e.g., 'Done')
            if not event_time or not event_name:
                continue
            try:
                # Combine date and time directly without applying any manual offset
                start_time_obj = datetime.strptime(f"{event_date} {event_time}", '%Y-%m-%d %I:%M %p')

                # If event time is 12:00 AM or after, move it to the next day
                if start_time_obj.time().hour >= datetime.strptime('12:00 AM',
                                                             '%I:%M %p').time().hour and start_time_obj.time().hour < datetime.strptime(
                        '6:00 AM', '%I:%M %p').time().hour:
                    start_time_obj += timedelta(days=1)

                # Set the event end time to one hour later
                end_time_obj = start_time_obj + timedelta(hours=1)

                # Format the times in ISO 8601 format (keep local time and set timezone to PST)
                start_time = start_time_obj.isoformat()
                end_time = end_time_obj.isoformat()
            except ValueError:
                print(f"Skipping event '{event_name}' due to invalid time format: {event_time}")
                continue

            # Create event data for Google Calendar API
            event_data = {
                'summary': event_name,
                'start': {
                    'dateTime': start_time,
                    'timeZone': 'America/Los_Angeles',  # Set to PST
                },
                'end': {
                    'dateTime': end_time,
                    'timeZone': 'America/Los_Angeles',  # Set to PST
                },
                'colorId': '1'  # Optional: set color for events
            }

            # Insert event to Google Calendar
            try:
                event_result = service.events().insert(calendarId=calendar_id, body=event_data).execute()
                print(f"Event '{event_name}' created successfully from {start_time} to {end_time}.")
            except Exception as e:
                print(f"Failed to create event '{event_name}': {e}")


def delete_all_events(service, event_date):
    service = gcal_auth()

    # Set the calendar ID
    calendar_id = "rootkalyan@gmail.com"

    # Adjust the times to PST (UTC-8) and include until next day 3 AM
    pst_offset = timedelta(hours=-8)

    # Start time: the start of the event_date at 00:00 PST
    time_min = (datetime.strptime(f"{event_date} 00:00", '%Y-%m-%d %H:%M') - pst_offset).isoformat() + 'Z'

    # End time: 3 AM on the following day PST
    time_max = (datetime.strptime(f"{event_date} 03:00", '%Y-%m-%d %H:%M') + timedelta(
        days=1) - pst_offset).isoformat() + 'Z'

    # Fetch events between the time range
    events_result = service.events().list(calendarId=calendar_id, timeMin=time_min, timeMax=time_max,
                                          singleEvents=True, orderBy='startTime').execute()
    events = events_result.get('items', [])

    if not events:
        print(f"No events found from {event_date} until 3 AM the next day to delete.")
        return

    # Loop through each event and delete it
    for event in events:
        event_id = event['id']
        event_start = event['start'].get('dateTime', event['start'].get('date'))
        event_end = event['end'].get('dateTime', event['end'].get('date'))
        try:
            service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
            print(f"Event '{event['summary']}' (from {event_start} to {event_end}) deleted successfully.")
        except Exception as e:
            print(f"Failed to delete event '{event['summary']}' (from {event_start} to {event_end}): {e}")




def normalise_timeformat_items_eve(utc_time_str,pst_offset):
    utc_time = datetime.strptime(str(utc_time_str), '%Y-%m-%dT%H:%M:%S')
    pst_time = utc_time + pst_offset
    return pst_time.strftime('%Y-%m-%dT%H:%M:%S')


# Function to extract event details (name, start, end) into a list
def extract_event_data(items, event_date, pst_offset):
    event_list = []
    for item in items:
        for event_name, event_details in item.items():
            event_time = event_details['time']
            if not event_time or not event_name:
                continue
            try:
                # Convert item time to start and end times in PST
                item_start_time = datetime.strptime(f"{event_date} {event_time}", '%Y-%m-%d %I:%M %p') - pst_offset
                item_end_time = item_start_time + timedelta(hours=1)
                event_list.append({
                    'name': event_name,
                    'start': normalise_timeformat_items_eve(item_start_time.isoformat(),pst_offset),
                    'end': normalise_timeformat_items_eve(item_end_time.isoformat(),pst_offset)
                })
            except ValueError:
                print(f"Invalid time format for event '{event_name}' with time '{event_time}'")
                # return []
                continue
    print(event_list)
    return event_list



# Function to extract existing events from Google Calendar
def extract_existing_event_data(existing_events, pst_offset):
    event_list = []
    for event in existing_events:
        try:
            start_time = event['start']['dateTime']
            end_time = event['end']['dateTime']

            start_time_obj = datetime.strptime(str(start_time), '%Y-%m-%dT%H:%M:%S%z')
            end_time_obj = datetime.strptime(str(end_time), '%Y-%m-%dT%H:%M:%S%z')

            # Check if the time is between 12 AM and 6 AM
            # print (str(start_time_obj.time().hour) +" "+ \
            #        str(datetime.strptime('00:00:00', '%H:%M:%S').time().hour) +" "+\
            #        str(start_time_obj.time().hour)+" "+\
            #        str(datetime.strptime('06:00:00', '%H:%M:%S').time().hour))

            if start_time_obj.time().hour >= datetime.strptime('00:00:00', '%H:%M:%S').time().hour and \
                    start_time_obj.time().hour < datetime.strptime('06:00:00', '%H:%M:%S').time().hour:
                print("reducing by 1 day")
                start_time_obj -= timedelta(days=1)
                end_time_obj -= timedelta(days=1)

            event_list.append({
                'name': event['summary'],
                'start': start_time_obj.strftime('%Y-%m-%dT%H:%M:%S'),
                'end': end_time_obj.strftime('%Y-%m-%dT%H:%M:%S')
            })
        except KeyError:
            print(f"Missing start/end time for event '{event['summary']}'")
            continue
    print(event_list)
    return event_list


# Compare the two lists of events
def compare_event_lists(new_events, existing_events):
    if len(new_events) != len(existing_events):
        return True

    for new_event, existing_event in zip(new_events, existing_events):
        if (new_event['name'] != existing_event['name'] or
                new_event['start'] != existing_event['start'] or
                new_event['end'] != existing_event['end']):
            print(f"Event mismatch found: {new_event} != {existing_event}")
            return True
    return False


def compare_and_sync_events( items, event_date):
    service = gcal_auth()
    # Set the calendar ID and PST offset
    calendar_id = "rootkalyan@gmail.com"
    pst_offset = timedelta(hours=-7)

    # Time range: from midnight on the event_date to 3 AM the next day (all in PST)
    time_min = (datetime.strptime(f"{event_date} 00:00", '%Y-%m-%d %H:%M') - pst_offset).isoformat() + 'Z'
    time_max = (datetime.strptime(f"{event_date} 03:00", '%Y-%m-%d %H:%M') + timedelta(
        days=1) - pst_offset).isoformat() + 'Z'

    # Get existing events from the calendar
    events_result = service.events().list(calendarId=calendar_id, timeMin=time_min, timeMax=time_max,
                                          singleEvents=True, orderBy='startTime').execute()
    existing_events = events_result.get('items', [])

    # Extract event details for comparison
    new_event_list = extract_event_data(items, event_date, pst_offset)
    existing_event_list = extract_existing_event_data(existing_events,pst_offset)

    # Compare the event lists
    if compare_event_lists(new_event_list, existing_event_list):
        print("Changes detected, deleting and re-adding events.")
        delete_all_events(service, event_date)
        create_events_from_items(service, items, event_date)
    else:
        print("No changes detected.")


# Get today's date dynamically
# today_date = datetime.utcnow().strftime('%Y-%m-%d')
# print(today_date)

tmrw_date = (datetime.utcnow() + timedelta(days=1)).strftime('%Y-%m-%d')
print(tmrw_date)
create_sample_eve(gcal_auth(),tmrw_date)

# # Call the function with today's date
# create_events_from_items(service,items, today_date)
# time.sleep(3)
# delete_all_events(service,today_date)
# sys.exit(0)

# while True :
#     compare_and_sync_events( items, today_date)
#     time.sleep(3)


# # Create a new calendar
# new_calendar = {
#     'summary': 'scheduler_app',
#     'timeZone': 'America/Los_Angeles'
# }
#
# created_calendar = service.calendars().insert(body=new_calendar).execute()
# calendar_id = created_calendar['id']
# print(f"Created calendar: {calendar_id}")
#
# # Grant permission to another user
# permission = {
#     'role': 'writer',  # You can also use 'owner', 'reader', etc.
#     'scope': {
#         'type': 'user',
#         'value': 'rootkalyan@gmail.com'  # Replace with the email to grant access
#     }
# }
#
# service.acl().insert(calendarId=calendar_id, body=permission).execute()
# print(f"Granted permissions to rootkalyan@gmail.com")
