from flask import Flask, jsonify, request, copy_current_request_context, current_app
from flask_socketio import SocketIO, emit
import logging
from datetime import datetime
import time
import threading
import logging
import time
from math import sqrt



from datetime import datetime ,timedelta
from plyer import notification
import threading
import logging

import pygsheets
import xlsxwriter

from telegram import Bot
from telegram.ext import Updater, CommandHandler, MessageHandler, filters, CallbackContext
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CallbackQueryHandler, CommandHandler, MessageHandler, Filters
import asyncio
import eventlet





app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading",async_handlers=True)



class CustomFormatter(logging.Formatter):
    """Logging colored formatter, adapted from https://stackoverflow.com/a/56944256/3638629"""

    grey = '\x1b[38;21m'
    blue = '\x1b[38;5;39m'
    yellow = '\x1b[38;5;226m'
    red = '\x1b[38;5;196m'
    bold_red = '\x1b[31;1m'
    reset = '\x1b[0m'

    def __init__(self, fmt):
        super().__init__()
        self.fmt = fmt
        self.FORMATS = {
            logging.DEBUG: self.grey + self.fmt + self.reset,
            logging.INFO: self.blue + self.fmt + self.reset,
            logging.WARNING: self.yellow + self.fmt + self.reset,
            logging.ERROR: self.red + self.fmt + self.reset,
            logging.CRITICAL: self.bold_red + self.fmt + self.reset
        }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)
# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)
# # Define format for logs
# fmt = '%(asctime)s | %(levelname)8s | %(message)s'
# # Create stdout handler for logging to the console (logs all five levels)
# stdout_handler = logging.StreamHandler()
# stdout_handler.setLevel(logging.DEBUG)
# stdout_handler.setFormatter(CustomFormatter(fmt))
# # Add both handlers to the logger
# logger.addHandler(stdout_handler)




# @app.before_request
# def before_request():
#     logger.info(f'[{datetime.now()}] {request.method} {request.url}')
#     logger.info(f'Headers: {dict(request.headers)}')
#     if request.method in ['POST', 'PUT', 'PATCH']:
#         logger.info(f'Body: {request.get_json()}')

@socketio.on('connect')
def handle_connect():
    logger.debug(f'[{datetime.now()}] WebSocket connect')
    emit('connected', {'status': 'connected'})

@socketio.on('disconnect')
def handle_disconnect():
    logger.debug(f'[{datetime.now()}] WebSocket disconnect')

@socketio.on('send_notification')
def send_notification(message):
    logger.info(f'[{datetime.now()}] WebSocket send_notification: {message}')
    emit('notification', {'message': message})
    # @copy_current_request_context
    # def foo_main():
    #     emit('notification', {'message': message})
    # threading.Thread(target=foo_main).start()

def send_notification_notsocket(message):
    logger.info(f'[{datetime.now()}] WebSocket send_notification: {message}')
    socketio.emit('notification', {'message': message})

def handle_get_items_notsocket():
    global items
    logger.debug(f'[{datetime.now()}] WebSocket get_items request received')
    # Sample array of items
    # refresh_worksheet_buttons_matrix()

    socketio.emit('items', {'item': items})
    logger.info(f'[{datetime.now()}] WebSocket get_items response sent: {items}')


def find_task_last_row(all_values, column_index):
    """
    Finds the last non-empty row in the given column of the worksheet.

    Args:
        worksheet (Worksheet): The worksheet object.
        column_index (int): The index of the column to search.

    Returns:
        int: The last non-empty row index.
    """
    for row_index in range(len(all_values)):
        if all_values[row_index][column_index].strip() == '':  # Check if the cell is empty
            return row_index - 1
    return len(all_values) - 1  # Return the last row index if no empty cell is found

def get_column_letter(column_index):
    start_index = 1  # it can start either at 0 or at 1
    letter = ''
    while column_index > 25 + start_index:
        letter += chr(65 + int((column_index - start_index) / 26) - 1)
        column_index = column_index - (int((column_index - start_index) / 26)) * 26
    letter += chr(65 - start_index + (int(column_index)))
    return letter


def extend_task(worksheet, day_name, current_task, current_row_index, column_index):
    try:
        print("extend_task func: extending the next tasks by 1hr ")
        global all_values, items, cell_color_modes
        # spreadsheet = get_spreadsheet()
        # worksheet = get_worksheet(spreadsheet, "YourWorksheetName")  # Replace with your worksheet name

        # # Mark the current task as complete
        # change_cell_background_color(worksheet, current_row_index, column_index,
        #                              cell_color_modes['done_CELL_COLOR'])

        # Get the total number of rows in the worksheet
        num_rows = find_task_last_row(all_values, column_index)

        # # Check if we can extend the task within the bounds of the worksheet
        if current_row_index >= num_rows-1:
            print("Cannot extend the task: Already at the last row.")
            return
        # Shift each task in the next row in the day column down by one row
        # cell_list = all_values.range(current_row_index + 1, column_index + 1, num_rows, column_index + 1)
        cell_list = []
        for row in all_values[current_row_index:num_rows + 1]:
            cell = row[column_index:column_index + 1]
            cell_list.append(cell)

        for i in range(len(cell_list) - 1, 0, -1):
            cell_list[i] = cell_list[i - 1]
        cell_list[0] = cell_list[1]
        # cell_list = [cell_list]
        print("vals after selected cell "+str(cell_list)+" ")

        # Construct range string for update
        column_letter = get_column_letter(column_index+1)
        start_range = f"{column_letter}{current_row_index+1}"
        end_range = f"{column_letter}{num_rows + 1}"
        range_to_update = f"{start_range}:{end_range}"
        print("range getting updated "+range_to_update)
        # Update the values in the worksheet using batch update
        worksheet.update_values_batch([range_to_update], [cell_list], 'ROWS')

        print("Values updated successfully.")





    except Exception as e:
        logger.error(f"Error in method extend_task : {str(e)}")

@socketio.on('button_click')
def handle_button_click(button_json_response):
    global current_day, current_cell, worksheet
    try:
        label = button_json_response.get('label')
        action = button_json_response.get('action')
        reason = button_json_response.get('reason')
        time = button_json_response.get('time')

        print(f'Button clicked: Label={label}, Action={action}, Reason={reason}')
        logger.debug(f'[{datetime.now()}] WebSocket button_click: {button_json_response}')

        related_msg = label  # Assuming label contains the message details
        related_msg_time = time
        related_msg_day = current_day

        # start_row_index, end_row_index, column_index = `find_sheet_timerange_indexs`(related_msg_time, related_msg_day)
        start_row_index, column_index = find_task_position(related_msg_time, related_msg_day)

        print(f"Button: '{action}' pressed for the msg '{related_msg}' at {related_msg_day} {related_msg_time}!")

        if action == "Done":
            change_cell_background_color(worksheet, start_row_index, column_index,
                                         cell_color_modes['done_CELL_COLOR'])
            response_message = f"{related_msg} Task marked as done!"
        elif action == "Not Done":
            change_cell_background_color(worksheet, start_row_index, column_index,
                                         cell_color_modes['not_done_CELL_COLOR'])
            worksheet.update_value( xlsxwriter.utility.xl_rowcol_to_cell_fast(start_row_index,column_index+1) , reason)
            response_message = f"{related_msg} Task marked as not done!"
        elif action == "Extend":
            change_cell_background_color(worksheet, start_row_index, column_index,
                                         cell_color_modes['done_CELL_COLOR'])
            # current_row_index, column_index = find_task_position(day_name, time)
            extend_task(worksheet,current_day, label, start_row_index, column_index)

            response_message = f"{related_msg} after this task, will be extended!"
            # Implement the extend functionality here
        elif action == "Later":
            change_cell_background_color(worksheet, start_row_index, column_index,
                                         cell_color_modes['not_done_CELL_COLOR'])
            response_message = f"{related_msg} Task will be moved to later tasks!"
            # Implement the later functionality here
        refresh_worksheet_buttons_matrix(current_day)
        emit('button_click_ack', {'status': 'success', 'label': label})
    except Exception as e:
        logger.error(f"Error processing button click event: {str(e)}")
        emit('button_click_ack', {'status': 'error', 'message': str(e)})


# def button_click(data):
#     button_label = data.get('label')
#     logger.debug(f'[{datetime.now()}] WebSocket button_click: {data}')
#     print(f'Button clicked: {button_label}')
#     emit('button_click_ack', {'status': 'success', 'label': button_label})

# gsheet_start = False
items = [
  {'bath ': {'color': 'white', 'time': '8:00 AM', 'actual_done': ''}},
  {'work': {'color': 'white', 'time': '9:00 AM', 'actual_done': ''}}
]

@socketio.on('get_items')
def handle_get_items(data):
    global items
    logger.debug(f'[{datetime.now()}] WebSocket get_items request received')
    # Sample array of items
    # refresh_worksheet_buttons_matrix()

    emit('items', {'item': items})
    logger.info(f'[{datetime.now()}] WebSocket get_items response sent: {items}')
    # if not gsheet_start:
    #     print('Start pygsheets task')
    #     socketio.start_background_task(run_pygsheets, current_app._get_current_object())
    #     gsheet_start = True


    # send_notification(time.strftime("%H:%M:%S"))

# @app.route('/send_notification', methods=['POST'])
# def send_notification():
#     data = request.json
#     message = data.get('message', 'Default message')
#     socketio.emit('notification', {'message': message})
#     return jsonify({'status': 'success', 'message': message})

# @app.route('/trigger_notification', methods=['GET'])
# def trigger_notification():
#     message = {'message': 'This is a test notification from the server'}
#     socketio.emit('notification', message)
#     logger.info(f'[{datetime.now()}] trigger_notification executed')
#     return jsonify({'status': 'success', 'message': 'Notification triggered'})


@app.route('/log')
def log():
    socketio.emit('log', {'message': 'This is a log message'})
    return ''




# TOKEN_FILE = "gsheet_token_serviceacc_key.json"
# Function to authenticate with Google Sheets
def authenticate():
    try:
        # Try to load the token from the file
        gc = pygsheets.authorize(service_file =TOKEN_FILE)
        print("gsheet_auth_successs")
        # gc = pygsheets.authorize(client_secret=TOKEN_FILE)
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
    global cell_color_modes
    old_cell_color = worksheet.cell(((row_index ), (column_index + 1))).color
    print("prev_cell color = " + str(old_cell_color)  )

    if old_cell_color == cell_color_modes['current_CELL_COLOR']:
        change_cell_background_color(worksheet, row_index-1, column_index, cell_color_modes['unused_CELL_COLOR'])
        print("trigger: prev_cell color = "+ str(old_cell_color) )
    change_cell_background_color(worksheet, row_index, column_index, cell_color_modes['current_CELL_COLOR'])


def find_sheet_timerange_indexs(row_val, col_val):
    global all_values
    try:
        # Find the row indices for timestamps that enclose the current_time
        start_row_index = None
        end_row_index = None

        for i, row in enumerate(all_values):
            if not row or len(row) == 0:
                continue

            if row[0] :
                try:
                    start_time = datetime.strptime(row[0], "%I:%M %p")
                except ValueError:
                    print("error in find_sheet_timerange_indexs finding start_time"+str(row[0]) )
                    start_time = None

                if i < len(all_values) - 1 and all_values[i + 1] and len(all_values[i + 1]) > 0:
                    try:
                        end_time = datetime.strptime(all_values[i + 1][0], "%I:%M %p")
                    except ValueError:
                        print("error in find_sheet_timerange_indexs finding end_time"+str(all_values[i + 1][0]) )
                        end_time = None
                    try:
                        if (start_time and end_time and start_time <= datetime.strptime(row_val, "%I:%M %p") < end_time) or (start_time.hour == 11 and datetime.strptime(row_val, "%I:%M %p").hour == 11) or (start_time.hour == 23 and datetime.strptime(row_val, "%I:%M %p").hour == 23)   :
                            start_row_index = i
                            end_row_index = i + 1
                            break
                    except Exception as e:
                        print("error in find_sheet_timerange_indexs populating row_index "+str(e) )
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
                if cell_value == col_val:
                    column_index = j
                    if 0 <= start_time.hour < 6 and column_index > 1:  # time is between 12am and 5am and column_index>1
                        column_index = column_index - 2
                    else:
                        column_index = column_index
                    break
        # elif start_row_index is None or end_row_index is  None:
        #     print(all_values)

        print("start_time found to be "+str(start_time)+" end_time "+str(end_time)  )
        print("Current row1/row2/col index",start_row_index,end_row_index,column_index)
        return start_row_index, end_row_index, column_index
    except Exception as e:
        logger.error(f"Error in method find_sheet_timerange_indexs : {str(e)}")
        return []

def number_to_letter_notation(column_int):
    start_index = 1  # it can start either at 0 or at 1
    letter = ''
    while column_int > 25 + start_index:
        letter += chr(65 + int((column_int - start_index) / 26) - 1)
        column_int = column_int - (int((column_int - start_index) / 26)) * 26
    letter += chr(65 - start_index + (int(column_int)))

def refresh_worksheet_buttons_matrix(current_day):
    global all_values, cells_objs, worksheet, items
    all_values = worksheet.get_all_values()
    cells_objs = worksheet.get_all_values(returnas='cell', include_tailing_empty_rows=False)
    items = fetch_column_data_by_day(current_day)
    handle_get_items_notsocket()
    # print(str(len(all_values))+"-> allval , "+str(len(cells_objs))+"-> cells objs")


def find_task_position(task_time,day_name):# finding the task name when button clicked
    """
    Find the row and column index for the task based on the given day name and task time.

    Args:
        day_name (str): The name of the day (e.g., 'Monday').
        task_time (str): The time of the task (e.g., '08:00AM').

    Returns:
        tuple: (row_index, column_index) of the task position if found, otherwise (-1, -1).
    """
    global all_values

    try:
        # Ensure we have data
        if not all_values or not all_values[0]:
            raise ValueError("Sheet data is not available or empty.")

        # Find the column index for the given day name
        if day_name not in all_values[0]:
            raise ValueError(f"Day name '{day_name}' not found in the sheet headers.")

        column_index = all_values[0].index(day_name)

        # Find the row index for the given task time
        row_index = -1
        for idx, row in enumerate(all_values):
            if row[0].strip() == task_time.strip():
                row_index = idx
                hour = datetime.strptime(task_time, "%I:%M %p").hour
                current_hour = datetime.now().hour
                if hour ==0 or (hour < 3 and hour > 0):
                    column_index = column_index -2
                    print(" moving to before day since between 12-3am ")
                elif current_hour == 0 or (current_hour < 3 and current_hour > 0):
                    column_index = column_index - 2
                    print(" moving to before day since current time is 12-3am ")
                break

        if row_index == -1:
            raise ValueError(f"Task time '{task_time}' not found in the sheet.")

        return row_index, column_index

    except Exception as e:
        print(f"Error finding task position: {str(e)}")
        return -1, -1



all_values = ""
cells_objs = ""
worksheet = ""
cell_color_modes = ""
worksheet_name = ""
TOKEN_FILE = ""
gsheet_name = ""
gsheet =""
column_data_cache = {}
cell_color_modes={
    'current_CELL_COLOR':(0.20392157, 1, 0.20392157, 0),#light green
    'unused_CELL_COLOR' : (1, 1, 1, .3),#white
    'done_CELL_COLOR' : (0.6, 0.6, 0.9, .3),#light blue
    'not_done_CELL_COLOR' : (0.8, 0.4, 0.4, .3)#light red
}
current_day = ""
# known_colors = {
#     "green": (0.0, 1.0, 0.0, 0),
#     "red": (1.0, 0.0, 0.0, 0),
#     "blue": (0.6, 0.6, 0.8980392, 0),
#     "white": (1.0, 1.0, 1.0, 0),
#     "yellow": (1.0, 1.0, 0.0, 0),
#     "light blue": (0.6, 0.6, 0.8980392, 0)  # Example of a specific color
# }


def clear_ranges(worksheet, gc, list_non_delete):
    global all_values, cells_objs
    updated_all_val = all_values.copy()
    actual_done_col_indices = []

    ranges = 'A1:W100'
    """
    Clears multiple ranges of cells in the worksheet.

    Args:
        worksheet (pygsheets.Worksheet): The worksheet object.
        ranges (list of tuple): A list of tuples, each containing the start and end cell in A1 notation (e.g., [('A1', 'B2'), ('C3', 'D4')]).

    Returns:
        None
    """
    try:
        requests = [
            {
                "repeatCell": {
                    "range": test_worksheet.get_gridrange("B2", "O21"),
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": {"red": 1, "green": 1, "blue": 1}
                        }
                    },
                    "fields": "userEnteredFormat.backgroundColor",
                }
            }
        ]
        gc.sheet.batch_update(gsheet.id, requests)
        # Find the index of the "actual done" column
        header_row = updated_all_val[0]
        for idx, col_value in enumerate(header_row):
            if col_value.lower() == "actual done":
                actual_done_col_indices.append(idx)

        for row_idx in range(1, 21):  # Skip the first row
            for col_idx in range(1, len(updated_all_val[row_idx])):  # Skip the first column
                cell_value = updated_all_val[row_idx][col_idx]

                if col_idx in actual_done_col_indices:
                    updated_all_val[row_idx][col_idx] = ""

                elif cell_value and not any(keyword in cell_value.lower() for keyword in list_non_delete):
                    updated_all_val[row_idx][col_idx] = ""

        # worksheet.clear(ranges=ranges)
        worksheet.update_values(ranges,updated_all_val )

        print(f"Cleared the ranges: {', '.join(ranges)}")
    except Exception as e:
        print(f"Error clearing ranges {ranges}: {str(e)}")


def fetch_column_data_by_day(day_name):# updating the list of buttons to be shown in the app
    global all_values, worksheet, cells_objs, column_data_cache
    try:
        # print("all_values: ", str(all_values))
        # print("cell_obj: ", str(cells_objs))
        if not all_values or not all_values[0]:
            logger.error("Sheet headers not found.")
#             print("Sheet headers not found.")
            return []

        if day_name not in all_values[0]:
            logger.error(f"Day name '{day_name}' not found in the sheet headers.")
#             print(f"Day name '{day_name}' not found in the sheet headers.")
            return []

#         print("Sheet headers: ", str(all_values[0]))
        column_index = all_values[0].index(day_name)
#         print("Column index for day name: ", column_index)
        hour = datetime.now().hour
        if hour == 0 or (hour < 3 and hour > 0):
            if column_index >1: # not monday
                column_index = column_index - 2
            else :# specifically for monday >> getting sundays list
                column_index = len(all_values[0])-2
            print(" moving to before day since between 12-3am ")

        column_data = []
        for row in all_values[1:]:  # Exclude the header row
#             print("Current row: ", str(row))
            cell_value = row[column_index]
            actual_done_value = row[column_index+1]
#             print("Cell value: ", cell_value)
            row_index = all_values.index(row)
#             print("Row index: ", row_index)
            cell = cells_objs[row_index][column_index]  # Corrected index
#             print("Cell object: ", str(cell))
            cell_color = cell.color
#             print(cell_value + " >> " + str(cell_color))
            color_name = get_color_name(cell_color)
#             print("Color name: ", color_name)
            time_value = row[0]
            # column_data.append({cell_value: color_name})
            column_data.append( {cell_value: {"color": color_name,"time": time_value,"actual_done": actual_done_value}} )


#         print("Column data: ", str(column_data))
        column_data_cache[day_name] = column_data
        return column_data

    except Exception as e:
        logger.error(f" fetch_column_data_by_day func error with '{day_name}' .{str(e)}")
        print(f" fetch_column_data_by_day func error with '{day_name}' .{str(e)}")
        return []

def get_color_name(color_tuple):
    if color_tuple == (0.20392157, 1, 0.20392157, 0):
        return "green"
    elif color_tuple == (0.8, 0.4, 0.4, 0):
        return "red"
    elif color_tuple == (0.6, 0.6, 0.8980392, 0):
        return "blue"
    elif color_tuple == (1, 1, 1, 0):
        return "white"
    else:
        return "white"




# @socketio.on('gsheets')
def run_pygsheets():
    # global app
    # Authenticate or load the saved token
    global all_values ,current_cell,current_day , cells_objs , worksheet , cell_color_modes, worksheet_name, TOKEN_FILE, gsheet_name, gsheet, cell_color_modes, items
    logger.debug("run_pygsheets started")
    TOKEN_FILE = "sheets-python-integrate-587cd0e2df13.json"
    time.sleep(5)

    gc = authenticate()

    # Open the Google Sheet
    # gsheet = gc.open(gsheet_name)
    gsheet = gc.open_by_key("1XyG8MYwwpCvWg-yvCjS8uu2Ra93uIGIc2K3_qMGlEyY")

    gsheet_name = 'gsheet-python'
    # worksheet_name = 'testtimetable'#test sheet
    worksheet_name = 'Timetable'  # orignal sheet
    current_cell = {
        'row_index': None,
        'col_index': None
    }

    # print(all_values)
    past_min = datetime.now().minute - 1

    while True:
        try:
            current_min = datetime.now().minute
            if current_min != past_min:  # hour changed, execute the while syntax after it
                past_min = current_min
                print("iteration :------------------->>")
            else:  # hour didnt change
                time.sleep(50)
                continue

            # Define the current day and time
            current_day = datetime.now().strftime("%A")  # e.g., "Monday"
            current_time = datetime.now().strftime("%I:%M %p")  # e.g., "03:30 PM"
            print("Current dateime", current_time, current_day)

            # Authenticate or load the saved token
            gc = authenticate()
            # Open the Google Sheet
            # gsheet = gc.open(gsheet_name)
            gsheet = gc.open_by_key("1XyG8MYwwpCvWg-yvCjS8uu2Ra93uIGIc2K3_qMGlEyY")
            worksheet_name = worksheet_name
            worksheet = gsheet.worksheet('title', worksheet_name)

            # Get all values from the worksheet as a 2D array
            refresh_worksheet_buttons_matrix(current_day)

            previous_day = (datetime.now() - timedelta(days=1)).strftime("%A")


            # Execute the clear function only if it's moving from Sunday to Monday
            if previous_day == "Sunday" and current_day == "Monday":
                clear_ranges(worksheet,gc, ["lunch", "dinner", "work"])

            start_row_index, end_row_index, column_index = find_sheet_timerange_indexs(current_time, current_day)

            #test notification
            # send_notification_notsocket("prev_task" + " completed?")
            # Extract the tasks from the corresponding cells, if found
            if (
                    start_row_index is not None and start_row_index != current_cell['row_index']
                    and end_row_index is not None
                    and column_index is not None
            ):
                current_cell['row_index'] = start_row_index
                current_cell['end_row_index'] = end_row_index
                current_cell['col_index'] = column_index
                current_cell['worksheet'] = worksheet

                start_task = all_values[current_cell['row_index']][current_cell['col_index']]
                end_task = all_values[current_cell['end_row_index']][current_cell['col_index']]
                prev_task = all_values[current_cell['row_index'] - 1][current_cell['col_index']]
                prev_task_time = (datetime.strptime(current_time, "%I:%M %p") - timedelta(hours=1, minutes=0)).strftime(
                    "%I:%M %p")
                print("Current task :", start_task)
                print("Upcoming task :", end_task)

                # update the cell colors every hour
                hour_change_cell_color_update(current_cell['worksheet'], current_cell['row_index'],
                                              current_cell['col_index'])

                notification_title = "Current Tasks"
                notification_text = (
                    f"{current_day}, {current_time} - {end_task}: {start_task}"
                )
                # send_notification_notsocket(str(notification_title+notification_text))
                send_notification_notsocket(prev_task+" completed?")

            elif (start_row_index is not None and end_row_index is not None and column_index is not None):
                curr_task = all_values[start_row_index][column_index]
                print("Same task as before " + curr_task)
            else:
                print("No tasks found at the current time.")
                print("Its sleep time ! zzZ")
                # with app.app_context():
                # send_notification_notsocket("Its sleep time ! zzZ")
        except Exception as e:
            logger.error("Error during main method: %s", str(e))
            # error_intimate_message("Error during main method: %s" + str(e))


# def start_code():


if __name__ == '__main__':
    # Create a thread to run the Flask app
    gsheet_thread = threading.Thread(target=run_pygsheets)
    # Start the Flask thread
    gsheet_thread.start()


    # socketio.start_background_task(run_pygsheets)
    socketio.run(app, host='0.0.0.0', port=5001, allow_unsafe_werkzeug=True, debug=True)
    print(">>>>>>> socket server started ")













'''
progressed:
- Basic buttons are being shown in the android app and continuosuly polled
- Android app is able to connect with flask for data transfer using websocket with reliable re-connect mechanism
- the app stays always open with foreground service feature 
- getting andriod notifications whenever flask server is sending a notification message to android app
- updating the buttons with respective color on andorid
- buttons ui needs to be scrollable and time needs to be shown adjacent to buttons
- Callback functions for button on android, after clicking each of ["done", "not done", "extend", "later"], in a new android page. beside "not done" and "later" there needs to be a textbox as well asking what did now 
- andorid when clicking on notification,  opening app 
- "extend" functionality added 
- actual done tasks being shown in another column besides the button in android 
- resolved > when clicking on tasks after 12pm, its changing in the next days tasks and not current days tasks due to difference in find_task_position and find_sheet_timerange_indexs methods 
- weekly refresh : where all colors and actual dones are cleared 
        when fixed task is seen like work, lunch, dinner which are fixed every day, then dont delete them while weekly refresh




pending tasks:
- android app: 
        
    
- flask app :
    in weekly refresh, add way to clear actual_done column too 
    host it on public port and add https cert auth via public port 
    when <task-section> is seen in gsheet instead of single task, then section needs to be pulled from the respective sections' gsheet for populating the buttons array 
    functionality for android button press , "later", needs to be added on server
    with "extend", routine timings like lunch and dinner should be moved, add a rotuine task list in another sheet 
    later button should change the current task in planned column itself and mark it completed
    
    
 




- Creating a better UI with buttons
- Optimise battery life, By checking one minute


'''