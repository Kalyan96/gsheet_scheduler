import time

import pygsheets
from datetime import datetime
from plyer import notification


from telegram import Bot
from telegram.ext import Updater, CommandHandler, MessageHandler, filters, CallbackContext
import asyncio

# Define the path to the token file
TOKEN_FILE = "gsheet_token.json"

# Function to authenticate with Google Sheets
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

def change_cell_background_color(worksheet, row_index, column_index, color):
    worksheet.cell(((row_index + 1), (column_index + 1))).color = color
    # worksheet.update_value((row_index + 1), (column_index + 1), worksheet.cell((row_index + 1), (column_index + 1)).value)

#sequence of color changes to be done in the cells every hour
def hour_change_cell_color_update(worksheet, row_index, column_index):
    global unused_CELL_COLOR, current_CELL_COLOR
    change_cell_background_color(worksheet, row_index-1, column_index, unused_CELL_COLOR)
    change_cell_background_color(worksheet, row_index, column_index, current_CELL_COLOR)


def find_sheet_timerange_indexs(row_val, col_val):
    global all_values
    # Find the row indices for timestamps that enclose the current_time
    start_row_index = None
    end_row_index = None

    for i, row in enumerate(all_values):
        if not row or len(row) == 0:
            continue

        if row[0] and row[0] != current_time:
            try:
                start_time = datetime.strptime(row[0], "%I:%M %p")
            except ValueError:
                start_time = None

            if i < len(all_values) - 1 and all_values[i + 1] and len(all_values[i + 1]) > 0:
                try:
                    end_time = datetime.strptime(all_values[i + 1][0], "%I:%M %p")
                except ValueError:
                    end_time = None

                if (start_time and end_time and start_time <= datetime.strptime(current_time, "%I:%M %p") < end_time) or (start_time.hour == 11 and datetime.strptime(current_time, "%I:%M %p").hour == 11) or (start_time.hour == 23 and datetime.strptime(current_time, "%I:%M %p").hour == 23)   :
                    start_row_index = i
                    end_row_index = i + 1
                    break
                # elif start_time == datetime.strptime("11:00 PM" , "%I:%M %p") and end_time == datetime.strptime("11:00 AM", "%I:%M %p"):#corner cases when time compares dont work
                #     start_row_index = i
                #     end_row_index = i + 1
                #     break
                # elif start_time == datetime.strptime("11:00 AM", "%I:%M %p") and end_time == datetime.strptime("12:00 PM", "%I:%M %p"):#corner cases when time compares dont work
                #     start_row_index = i
                #     end_row_index = i + 1
                #     break

    # Find the column index corresponding to the current day
    column_index = None
    if start_row_index is not None and end_row_index is not None:
        for j, cell_value in enumerate(all_values[0]):
            if cell_value == current_day:
                column_index = j
                break

    # print("start_time found to be "+str(start_time)+" end_time "+str(end_time)  )
    print("Current row1/row2/col index",start_row_index,end_row_index,column_index)
    return start_row_index, end_row_index, column_index

def send_message( message):
    global chat_id, token
    try:
        bot = Bot(token=token)
        bot.send_message(chat_id=chat_id, text=message)
    except Exception as e:
        logger.error("Error during telegram send message: %s", str(e))


token = '6538387137:AAEtL9aJvWxS_LLTW9vVn3gtfWd4aeM0Nlk'
chat_id = "6020027159"



# Define the color code for the notified cell (e.g., light green)
current_CELL_COLOR = (.204, 1, .204, .3)
#unused cell color
unused_CELL_COLOR = (1, 1, 1, .3)



# print(all_values)
past_hour = datetime.now().hour-1

while True :
    current_hour = datetime.now().hour
    if current_hour != past_hour:#hour changed
        past_hour = current_hour
    else : # hour didnt change
        time.sleep(60)
        continue

    # Authenticate or load the saved token
    gc = authenticate()

    # Open the Google Sheet
    gsheet = gc.open('gsheet-python')

    # Define the current day and time
    current_day = datetime.now().strftime("%A")  # e.g., "Monday"
    current_time = datetime.now().strftime("%I:%M %p")  # e.g., "03:30 PM"
    # current_time = "12:30 PM"

    print("Current dateime", current_time, current_day)

    # Access the worksheet where the timetable is stored (assuming it's named "Timetable")
    worksheet = gsheet.worksheet('title', 'Timetable')

    # Get all values from the worksheet as a 2D array
    all_values = worksheet.get_all_values()
    cells_objs = worksheet.get_all_values(returnas='cell', include_tailing_empty=False, include_tailing_empty_rows=False)
    # print(all_values)

    start_row_index, end_row_index, column_index = find_sheet_timerange_indexs(current_time, current_day)

    # Extract the tasks from the corresponding cells, if found
    if (
        start_row_index is not None
        and end_row_index is not None
        and column_index is not None
    ):
        start_task = all_values[start_row_index][column_index]
        end_task = all_values[end_row_index][column_index]
        print("Current task :",start_task)
        print("Upcoming task :",end_task)

        #update the cell colors every hour
        hour_change_cell_color_update(worksheet, start_row_index, column_index)
        send_message( "Current task : "+start_task+"\n | Upcoming task :"+end_task+"\n | Current dateime: "+current_time+" "+current_day)

        # notification_title = "Current Tasks"
        # notification_text = (
        #     f"{current_day}, {current_time} - {end_task}: {start_task}"
        # )
        # notification.notify(
        #     title=notification_title,
        #     message=notification_text,
        #     app_name="Timetable Reminder",
        # )
    else:
        print("No tasks found at the current time.")
        print("Its sleep time ! zzZ")


