import time

import pygsheets
from datetime import datetime


# Define the path to the token file
TOKEN_FILE = "gsheet_token.json"

def authenticate():
    try:
        # Try to load the token from the file
        gc = pygsheets.authorize(service_file=TOKEN_FILE)
    except FileNotFoundError:
        # If the token file doesn't exist, perform the initial authentication
        gc = pygsheets.authorize()

        # Save the authentication token to a file
        # gc.save_as(TOKEN_FILE)

    return gc

# Authenticate or load the saved token
gc = authenticate()

# Open the Google Sheet and work with it as before
gsheet = gc.open('gsheet-python')
spreadsheet = gsheet.worksheet('title','Sheet1')
print(spreadsheet.get_all_values())

while True :
    print(spreadsheet.get_values_batch( ['A1:1'] ))
    # spreadsheet.update_value('A8', datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
    time.sleep(1)
    # changes the time on sheet1 every second

