from flask import Flask, jsonify, request, copy_current_request_context, current_app
from flask_socketio import SocketIO, emit
import logging
from datetime import datetime
import time
import threading
import logging
import time
from math import sqrt
import requests
from google.oauth2 import service_account
from googleapiclient.discovery import build

from datetime import datetime, timedelta
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

import firebase_admin
from firebase_admin import credentials, messaging

app = Flask(__name__)
# socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading", async_handlers=True)
# fcm_token = ""
fcm_token = "cIzitcgDSPSRMcmLyTqTxt:APA91bHg7vvk_sVUcFMD75Ga-saRkZb8f6y3UBHi-txLL1ntBuyVoiH6ydKvP47cnjNS3Xg_9NG8B4e-DWYeZuadFB4RqbBDOm-nLMJbZ2B0EkNR1KQ1P7WSSlguewlLK3vRW04fpx8j"
# from android device
FCM_API_URL = 'https://fcm.googleapis.com/fcm/send'

cred = credentials.Certificate("schedulerv1-fcmsdk.json")
firebase_admin.initialize_app(cred)
mins_diff_to_trigger=1 # number of minutes to trigger the mobile notification, 1440mins=1day



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


@app.before_request
def before_request():
    source_add = dict(request.headers)
    # print(source_add["X-Forwarded-For"])
    logger.info(f'                            {source_add["X-Forwarded-For"]} >> {request.method} {request.url}')
    # logger.info(f'Headers: {dict(request.headers)}')
    # if request.method in ['POST', 'PUT', 'PATCH']:
    #     logger.info(f'Body: {request.get_json()}')

@app.route('/connect', methods=['POST'])
def handle_connect():
    logger.debug(f'[{datetime.now()}] HTTP connected')
    return jsonify({"status": "connected"})

@app.route('/get_items', methods=['POST'])
def handle_get_items():
    global items, current_day
    action = request.json.get('action')
    # refresh_worksheet_buttons_matrix(current_day)
    if action == "get_items":
        # Implement logic to fetch items here
        logger.debug(f'[{datetime.now()}] HTTP get_items: {items}')
        return jsonify({"status": "success", "items": items})
    return jsonify({"status": "error", "message": "Invalid action"}), 400


@app.route('/check_notification', methods=['POST']) # when client wants to check if there are any pending notifications
def check_notification():
    try:
        data = request.json
        logger.info(f'[{datetime.now()}] HTTP send_notification: {data}')

        # Process the incoming data (e.g., save it, trigger some action, etc.)
        # Respond with a JSON object indicating success or failure
        return jsonify({'status': 'success', 'message': 'Notification received', 'data': data}), 200
    except Exception as e:
        logger.error(f'Error processing notification: {str(e)}')
        return jsonify({'status': 'error', 'message': str(e)}), 500


# def send_notification_notsocket(message): # >> need to integrate FCM calling here
#     logger.info(f'[{datetime.now()}] WebSocket send_notification: {message}')
#     socketio.emit('notification', {'message': message})


# def handle_get_items_notsocket():# >> need to integrate FCM calling here
#     global items
#     logger.debug(f'[{datetime.now()}] WebSocket get_items request received')
#     # Sample array of items
#     # refresh_worksheet_buttons_matrix()
#
#     socketio.emit('items', {'item': items})
#     logger.info(f'[{datetime.now()}] WebSocket get_items response sent: {items}')


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
        if current_row_index >= num_rows - 1:
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
        print("vals after selected cell " + str(cell_list) + " ")

        # Construct range string for update
        column_letter = get_column_letter(column_index + 1)
        start_range = f"{column_letter}{current_row_index + 1}"
        end_range = f"{column_letter}{num_rows + 1}"
        range_to_update = f"{start_range}:{end_range}"
        print("range getting updated " + range_to_update)
        # Update the values in the worksheet using batch update
        worksheet.update_values_batch([range_to_update], [cell_list], 'ROWS')

        print("Values updated successfully.")





    except Exception as e:
        logger.error(f"Error in method extend_task : {str(e)}")


@app.route('/button_click', methods=['POST'])
def handle_button_click(): # when the android app replies with button click workflow, handling each buttons workflow
    try:
        button_json_response = request.json
        label = button_json_response.get('label')
        action = button_json_response.get('action')
        reason = button_json_response.get('reason')
        time = button_json_response.get('time')

        print(f'Button clicked: Label={label}, Action={action}, Reason={reason}')
        logger.debug(f'[{datetime.now()}] HTTP button_click: {button_json_response}')

        related_msg = label  # Assuming label contains the message details
        related_msg_time = time
        related_msg_day = current_day

        # start_row_index, end_row_index, column_index = `find_sheet_timerange_indexs`(related_msg_time, related_msg_day)
        start_row_index, column_index = find_task_position(related_msg_time, related_msg_day)

        print(f"Button: '{action}' pressed for the msg '{related_msg}' at {related_msg_day} {related_msg_time}!")

        if action == "Done":
            change_cell_background_color(worksheet, start_row_index, column_index, cell_color_modes['done_CELL_COLOR'])
            response_message = f"{related_msg} Task marked as done!"
        elif action == "Not Done":
            change_cell_background_color(worksheet, start_row_index, column_index, cell_color_modes['not_done_CELL_COLOR'])
            worksheet.update_value(xlsxwriter.utility.xl_rowcol_to_cell_fast(start_row_index, column_index + 1), reason)
            response_message = f"{related_msg} Task marked as not done!"
        elif action == "Extend":
            change_cell_background_color(worksheet, start_row_index, column_index, cell_color_modes['done_CELL_COLOR'])
            extend_task(worksheet, current_day, label, start_row_index, column_index)
            response_message = f"{related_msg} after this task, will be extended!"
        elif action == "Later":
            change_cell_background_color(worksheet, start_row_index, column_index, cell_color_modes['not_done_CELL_COLOR'])
            response_message = f"{related_msg} Task will be moved to later tasks!"
        elif action == "update_cell": # update the current task for current time
            # change_cell_background_color(worksheet, start_row_index, column_index, cell_color_modes['not_done_CELL_COLOR']) # no need to change cell background since updating the current task only
            worksheet.update_value(xlsxwriter.utility.xl_rowcol_to_cell_fast(start_row_index, column_index), reason)
            response_message = f"{related_msg} Task has been updated as current task!"
        else :
            response_message = f" Button click action {action} not defined !"
            logger.error(f"{response_message}")
            return jsonify({'status': 'success', 'label': label, 'message': response_message}), 500 # method breaks when incorrect button response code is seen
        # sleep(0.1)
        refresh_worksheet_buttons_matrix(current_day)

        # Send an HTTP response back to the client
        return jsonify({'status': 'success', 'label': label, 'message': response_message}), 200 # method is broken when incorrect response code seen ^^

    except Exception as e:
        logger.error(f"Error processing button click event: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/update_fcm', methods=['POST'])
def update_fcm():
    global fcm_token
    try:
        fcm_json_response = request.json
        if not ( fcm_json_response.get('fcm') == fcm_token) : # if FCM token has changed, then print and update
            fcm_token = fcm_json_response.get('fcm')
            print(f'FCM token updated: Token={fcm_token}')
            logger.info(f'[{datetime.now()}] FCM token updated: Token={fcm_token}')
        else :
            logger.debug(f'[{datetime.now()}] FCM token is the same : Token={fcm_token}')
        return jsonify({'status': 'success', 'message': "FCM token updated on python server"}), 200

    except Exception as e:
        logger.error(f"Error processing FCM token updation: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# def button_click(data):
#     button_label = data.get('label')
#     logger.debug(f'[{datetime.now()}] WebSocket button_click: {data}')
#     print(f'Button clicked: {button_label}')
#     emit('button_click_ack', {'status': 'success', 'label': button_label})

# gsheet_start = False
items = [
    {'APP INIT ': {'color': 'white', 'time': '8:00 AM', 'actual_done': ''}},
    {'trying to fetch from gsheet': {'color': 'white', 'time': '9:00 AM', 'actual_done': ''}}
]


# @socketio.on('get_items')
# def handle_get_items(data):
#     global items
#     logger.debug(f'[{datetime.now()}] WebSocket get_items request received')
#     # Sample array of items
#     # refresh_worksheet_buttons_matrix()
#
#     emit('items', {'item': items})
#     logger.info(f'[{datetime.now()}] WebSocket get_items response sent: {items}')
#     # if not gsheet_start:
#     #     print('Start pygsheets task')
#     #     socketio.start_background_task(run_pygsheets, current_app._get_current_object())
#     #     gsheet_start = True
#
#     # send_notification(time.strftime("%H:%M:%S"))



@app.route('/log')
def log():
    socketio.emit('log', {'message': 'This is a log message'})
    return ''



# send notification using FCM when HTTPs request is sent from android
@app.route('/send_notification', methods=['POST'])
def fcm_notify():
    # data = request.json
    # token = data.get('token')
    # title = data.get('title', 'Default Title')
    # body = data.get('body', 'Default Body')
    global fcm_token
    # token = "eQRtp5ISRDuP31HcbZpZKX:APA91bGzwN9HGxhnrZPD2kQsrD84qK8-dH51RGoF4XfhCOCuQmLE4UXsSVaG1CnSUyrz-GrM07GtkLxsqYjLbyCBIJ7rAtlftGcMGHAIgXOWTGjqD9v7VXkmndsC8J96M_qTwIAX5fOt"
    # token = fcm_token
    title = "App init connection"
    body = "requested by android app"

    if not fcm_token:
        return jsonify({'error': 'FCM token is required'}), 400


    # Define a message payload
    message = messaging.Message(
        data={
            'title': title,
            'body': body,
        },
        token=fcm_token,
    )

    # Send a message to the device corresponding to the provided registration token
    response = messaging.send(message)
    # Response is a message ID string
    return jsonify({'response': response})


# send notification using FCM independently
def fcm_notify_independent(title,body):
    # data = request.json
    # token = data.get('token')
    # title = data.get('title', 'Default Title')
    # body = data.get('body', 'Default Body')
    global fcm_token
    # token = "eQRtp5ISRDuP31HcbZpZKX:APA91bGzwN9HGxhnrZPD2kQsrD84qK8-dH51RGoF4XfhCOCuQmLE4UXsSVaG1CnSUyrz-GrM07GtkLxsqYjLbyCBIJ7rAtlftGcMGHAIgXOWTGjqD9v7VXkmndsC8J96M_qTwIAX5fOt"
    # title = "test notify"
    # body = "test data"

    if (fcm_token == ""):
        logger.error('error: FCM token is required, not present')


    # Define a message payload
    message = messaging.Message(
        data={
            'title': title,
            'body': body,
        },
        token=fcm_token,
    )

    # Send a message to the device corresponding to the provided registration token
    response = messaging.send(message)

    # Response is a message ID string
    logger.info('fcm_notify_independent : Successfully sent HTTP message:'+response)





# TOKEN_FILE = "gsheet_token_serviceacc_key.json"
# Function to authenticate with Google Sheets
def authenticate():
    try:
        # Try to load the token from the file
        gc = pygsheets.authorize(service_file=TOKEN_FILE)
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


# sequence of color changes to be done in the cells every hour
def hour_change_cell_color_update(worksheet, row_index, column_index):
    global cell_color_modes
    old_cell_color = worksheet.cell(((row_index), (column_index + 1))).color
    print("prev_cell color = " + str(old_cell_color))

    if old_cell_color == cell_color_modes['current_CELL_COLOR']:
        change_cell_background_color(worksheet, row_index - 1, column_index, cell_color_modes['unused_CELL_COLOR'])
        print("trigger: prev_cell color = " + str(old_cell_color))
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

            if row[0]:
                try:
                    start_time = datetime.strptime(row[0], "%I:%M %p")
                except ValueError:
                    print("error in find_sheet_timerange_indexs finding start_time" + str(row[0]))
                    start_time = None

                if i < len(all_values) - 1 and all_values[i + 1] and len(all_values[i + 1]) > 0:
                    try:
                        end_time = datetime.strptime(all_values[i + 1][0], "%I:%M %p")
                    except ValueError:
                        print("error in find_sheet_timerange_indexs finding end_time" + str(all_values[i + 1][0]))
                        end_time = None
                    try:
                        if (start_time and end_time and start_time <= datetime.strptime(row_val,
                                                                                        "%I:%M %p") < end_time) or (
                                start_time.hour == 11 and datetime.strptime(row_val, "%I:%M %p").hour == 11) or (
                                start_time.hour == 23 and datetime.strptime(row_val, "%I:%M %p").hour == 23):
                            start_row_index = i
                            end_row_index = i + 1
                            break
                    except Exception as e:
                        print("error in find_sheet_timerange_indexs populating row_index " + str(e))
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

        print("start_time found to be " + str(start_time) + " end_time " + str(end_time))
        print("Current row1/row2/col index", start_row_index, end_row_index, column_index)
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

temp_day_change_tracker=""
def refresh_worksheet_buttons_matrix(current_day):
    global all_values, cells_objs, worksheet, items, temp_day_change_tracker
    all_values = worksheet.get_all_values()
    cells_objs = worksheet.get_all_values(returnas='cell', include_tailing_empty_rows=False)
    items = fetch_column_data_by_day(current_day)
    update_all_values_dict_prop()
    reschedule_task_to_empty_slot()

    if datetime.now().time().hour >= datetime.strptime('12:00 AM',
                                                       '%I:%M %p').time().hour and datetime.now().time().hour < datetime.strptime(
        '6:00 AM', '%I:%M %p').time().hour:
        adjusted_datetime = datetime.now() - timedelta(days=1) # adjusting it when time is 12-3am next day
    else :
        adjusted_datetime = datetime.now()
    if temp_day_change_tracker != current_day:
        create_events_from_items(items, adjusted_datetime.strftime('%Y-%m-%d'))
        temp_day_change_tracker = current_day
        print("CAL events : day changed, Calendar full refreshed !!! ")
    else :
        compare_and_sync_events(items, adjusted_datetime.strftime('%Y-%m-%d'))
    # print(str(len(all_values))+"-> allval , "+str(len(cells_objs))+"-> cells objs")


def find_task_position(task_time, day_name):  # finding the task name when button clicked
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
                if hour == 0 or (hour < 3 and hour > 0):
                    column_index = column_index - 2
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
all_values_dict_prop = "" # all tasks values/properties/cell_objs >> check method
cells_objs = ""
worksheet = ""
cell_color_modes = ""
worksheet_name = ""
TOKEN_FILE = ""
gsheet_name = ""
gsheet = ""
column_data_cache = {}
cell_color_modes = {
    'current_CELL_COLOR': (0.20392157, 1, 0.20392157, 0),  # light green
    'unused_CELL_COLOR': (1, 1, 1, .3),  # white
    'done_CELL_COLOR': (0.6, 0.6, 0.9, .3),  # light blue
    'not_done_CELL_COLOR': (0.8, 0.4, 0.4, .3)  # light red
}
current_day = ""

caleve_color_modes = {
    'imp_task': 11,  # red
    'repeated_task': 8,  # lite green
    'planned_task': 9,  # dark blue
}

dont_clear_tasks = ["lunch", "dinner", "work", "kids pickup", "kids classes", "kids", "tea", "blocked", "going out"] # there are mostly the regular tasks, which also dont auto-reschedule



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

        notification_title = "Welcome to a new week !!"
        notification_text = "clearing the worksheet"
        fcm_notify_independent(notification_title, notification_text)

        print ("Skipping clear_range func, since the pending important tasks are also cleared, paused until thats fixed")
        return

        requests = [
            {
                "repeatCell": {
                    "range": worksheet.get_gridrange("B2", "O21"),
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
        worksheet.update_values(ranges, updated_all_val)

        print(f"Cleared the ranges: {', '.join(ranges)}")


    except Exception as e:
        print(f"Error clearing ranges {ranges}: {str(e)}")

def is_valid_time_format(time_str):
    try:
        # Check if the string can be parsed as a valid time (12-hour format)
        datetime.strptime(time_str, '%I:%M %p')
        return True
    except ValueError:
        return False


def sort_key(day_time_str):
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    day, time_str = day_time_str.split(" ", 1)

    # Convert the time string into a datetime object for sorting by time
    time_obj = datetime.strptime(time_str, '%I:%M %p')

    # If time is between 12 AM and 3 AM, consider it for the next day
    if time_obj.time() >= datetime.strptime('12:00 AM', '%I:%M %p').time() and time_obj.time() <= datetime.strptime(
            '03:00 AM', '%I:%M %p').time():
        day_index = (day_order.index(day) + 1) % 7  # Move to next day
    else:
        day_index = day_order.index(day)

    return (day_index, time_obj)


def update_all_values_dict_prop():
    global all_values, cells_objs, all_values_dict_prop
    nested_dict = {}
    time_vals = []
    # Get the header rows (first row contains day names, first column contains times)
    day_names = []
    for col_idx, col_value in enumerate(all_values[0][1:], start=1):
        # Stop when reaching empty columns or invalid values
        if col_value.strip() == "" or col_value.lower() not in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']:
            continue
        # Add the day name if valid and not an actual_done column (assuming even-indexed columns are days)
        if col_idx % 2 == 1:  # Day columns are odd-indexed, actual_done are even-indexed
            day_names.append(col_value)

    # Iterate through each row and column to build the nested dictionary
    for row_idx, row in enumerate(all_values[1:], start=1):  # Skip the header row
        time_value = row[0]

        # Skip rows with invalid time formats
        if not is_valid_time_format(time_value):
            continue
        time_vals.append(time_value)
        for col_idx, day_name in enumerate(day_names):
            day_time_key = f"{day_name} {time_value}"  # "dayname time" as the key
            task_name = row[1 + col_idx * 2]  # Task name in this column
            actual_done_value = row[2 + col_idx * 2]  # Actual done value (the adjacent column)
            cell = cells_objs[row_idx][1 + col_idx * 2]  # Get the cell object itself
            cell_color = cell.color  # Get the color of the task cell

            # Only add to dictionary if task_name is not empty
            nested_dict[day_time_key] = {
                task_name: {
                    "color": get_color_name(cell_color),
                    "actual_done": actual_done_value,
                    "cell_obj": cell  # Include the cell object itself
                }
            }

    # Sort the nested_dict by keys
    sorted_nested_dict = dict(sorted(nested_dict.items(), key=lambda item: sort_key(item[0])))
    all_values_dict_prop = sorted_nested_dict
    # return sorted_nested_dict


def reschedule_task_to_empty_slot():
    global current_day, all_values_dict_prop, dont_clear_tasks, worksheet
    current_time = datetime.now().time()
    current_day_local = current_day

    # Adjust current_day if current_time is between 12 AM and 3 AM
    try:
        if current_time >= datetime.strptime('12:00 AM', '%I:%M %p').time() and current_time <= datetime.strptime(
                '04:00 AM', '%I:%M %p').time():
            day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            current_day_index = day_order.index(current_day)
            current_day_local = day_order[(current_day_index - 1) % 7]  # Move to the previous day
    except ValueError as e:
        print(f"reschedule_task_to_empty_slot method: Error adjusting day based on time: {e}")
        return

    try:
        # Round current_time to the nearest previous full hour
        current_time_hour = (datetime.combine(datetime.today(), current_time) - timedelta(minutes=current_time.minute,
                                                                                          seconds=current_time.second,
                                                                                          microseconds=current_time.microsecond)).time()

        # Get the current task key (which is actually the key for the current time)
        current_task_key = f"{current_day_local} {datetime.now().strftime('%I:00 %p').lstrip('0')}"

        # Check if the current task key exists in the dictionary
        if current_task_key not in all_values_dict_prop:
            print(f"reschedule_task_to_empty_slot method: Current task key {current_task_key} not found in the dictionary.")
            return

        # Get the list of keys from the dictionary
        keys_list = list(all_values_dict_prop.keys())

        # Find the index of the current task key
        current_index = keys_list.index(current_task_key)
        # Create the rotated keys list


        keys_list_rotated = keys_list[current_index:] + keys_list[:current_index]        # Create the rotated all_values_dict_prop
        all_values_dict_prop_rotated = {key: all_values_dict_prop[key] for key in keys_list_rotated}
        current_index =0

        # Add a grace period of 15 minutes
        task_rescheduling_check_delay = 1
        current_task_start_time = datetime.strptime(current_task_key.split(' ', 1)[1], '%I:%M %p').time()
        current_task_start_time_plus_delay = (datetime.combine(datetime.today(), current_task_start_time) + timedelta(minutes=task_rescheduling_check_delay)).time()

        # Only proceed if the current time is after the grace period
        if current_time < current_task_start_time_plus_delay:
            print(f"reschedule_task_to_empty_slot method: Not enough time has passed since {current_task_key} start. Waiting for the {task_rescheduling_check_delay}-minute grace period.")
            return

        # Get the previous task key from the dictionary
        if current_index == 0:
            previous_task_key = keys_list_rotated[-1]  # Take the last task key if current_index is 0
        else:
            previous_task_key = keys_list_rotated[current_index - 1]

        # Check if the task exists and is not done (green) and not in dont_clear_tasks
        if previous_task_key in all_values_dict_prop_rotated:
            task_data = all_values_dict_prop_rotated[previous_task_key]
            task_name, task_info = next(iter(task_data.items()))  # Get task name and info

            # Skip if the task is empty
            if not task_name.strip():
                print(f"reschedule_task_to_empty_slot method: No task to reschedule at {previous_task_key}.")
                return

            task_color = task_info['color']

            if task_color != 'blue' and task_name not in dont_clear_tasks:
                # Iterate over future keys in the dictionary
                for future_index in range(current_index + 1, len(keys_list_rotated)):
                    future_task_key = keys_list_rotated[future_index]
                    future_task_data = all_values_dict_prop_rotated[future_task_key]

                    future_task_name, future_task_info = next(iter(future_task_data.items()))
                    if not future_task_name:  # Empty slot found
                        future_cell = future_task_info.get('cell_obj')
                        previous_cell = task_info.get('cell_obj')

                        if future_cell and previous_cell:
                            # Adjust the row and column indices (-1 for 1-based index)
                            future_row, future_col = future_cell.row - 1, future_cell.col - 1
                            previous_row, previous_col = previous_cell.row - 1, previous_cell.col - 1

                            # Clear the previous cell in the Google worksheet
                            worksheet.update_value(
                                xlsxwriter.utility.xl_rowcol_to_cell_fast(previous_row, previous_col),
                                "")  # Clear previous

                            # Move the task to the future empty cell in the Google worksheet
                            worksheet.update_value(xlsxwriter.utility.xl_rowcol_to_cell_fast(future_row, future_col),
                                                   task_name)  # Move task

                            print(f"reschedule_task_to_empty_slot method: Moved '{task_name}' from {previous_task_key} to {future_task_key}, since not-done, non-regular task")
                            return

                print("reschedule_task_to_empty_slot method: No empty future slot found.")

        else:
            print(f"reschedule_task_to_empty_slot method: No task found at the previous hour ({previous_task_key}).")

    except KeyError as e:
        print(f"reschedule_task_to_empty_slot method: Key error occurred: {e}")
    except Exception as e:
        print(f"reschedule_task_to_empty_slot method: An unexpected error occurred: {e}")


def fetch_column_data_by_day(day_name):  # updating the list of buttons to be shown in the app
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
            if column_index > 1:  # not monday
                column_index = column_index - 2
            else:  # specifically for monday >> getting sundays list
                column_index = len(all_values[0]) - 2
            print(" moving to before day since between 12-3am ")

        column_data = []
        for row in all_values[1:]:  # Exclude the header row
            #             print("Current row: ", str(row))
            cell_value = row[column_index]
            actual_done_value = row[column_index + 1]
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
            column_data.append(
                {cell_value: {"color": color_name, "time": time_value, "actual_done": actual_done_value}})

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


def get_caleve_color (event_name):
    global dont_clear_tasks, caleve_color_modes
    if event_name in dont_clear_tasks:
        return caleve_color_modes['repeated_task']
    else:
        return caleve_color_modes['planned_task']


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

def create_events_from_items( items, event_date):
    # Adjusting the time zone to PST (UTC-8) without manually modifying the time
    service = gcal_auth()
    timezone_offset = timedelta(hours=0)# 0 = pst offset, 2 = CST offsets
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
                if (start_time_obj.time().hour >= (datetime.strptime('12:00 AM','%I:%M %p')).time().hour and
                        start_time_obj.time().hour <= (datetime.strptime('6:00 AM', '%I:%M %p')).time().hour):
                    start_time_obj += timedelta(days=1)

                start_time_obj = start_time_obj-timezone_offset
                # Set the event end time to one hour later
                end_time_obj = start_time_obj + timedelta(hours=1)

                # Format the times in ISO 8601 format (keep local time and set timezone to PST)
                start_time = start_time_obj.isoformat()
                end_time = end_time_obj.isoformat()
            except ValueError:
                print(f"create_events_from_items method: Skipping event '{event_name}' due to invalid time format: {event_time}")
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
                'colorId': get_caleve_color(event_name)  # Optional: set color for events
            }

            # Insert event to Google Calendar
            try:
                event_result = service.events().insert(calendarId=calendar_id, body=event_data).execute()
                print(f"create_events_from_items method: Event '{event_name}' created successfully from {start_time} to {end_time}.")
            except Exception as e:
                print(f"create_events_from_items method: Failed to create event '{event_name}': {e}")


def delete_all_events(service, event_date, time_min, time_max):
    service = gcal_auth()

    # Set the calendar ID
    calendar_id = "rootkalyan@gmail.com"

    # Adjust the times to  (now CST)(UTC-6) or PST (UTC-8), and include until next day 3 AM
    # pst_offset = timedelta(hours=-7)

    # Start time: the start of the event_date at 00:00 PST
    # time_min = (datetime.strptime(f"{event_date} 00:00", '%Y-%m-%d %H:%M') - pst_offset).isoformat() + 'Z'

    # End time: 3 AM on the following day PST
    # time_max = (datetime.strptime(f"{event_date} 03:00", '%Y-%m-%d %H:%M') + timedelta(days=1) - pst_offset).isoformat() + 'Z'

    # Fetch events between the time range
    events_result = service.events().list(calendarId=calendar_id, timeMin=time_min, timeMax=time_max,
                                          singleEvents=True, orderBy='startTime').execute()
    events = events_result.get('items', [])

    if not events:
        print(f"delete_all_events method: No events found from {event_date} until 3 AM the next day to delete.")
        return

    # Loop through each event and delete it
    for event in events:
        event_id = event['id']
        event_start = event['start'].get('dateTime', event['start'].get('date'))
        event_end = event['end'].get('dateTime', event['end'].get('date'))
        try:
            service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
            print(f"delete_all_events method: Event '{event['summary']}' (from {event_start} to {event_end}) deleted successfully.")
        except Exception as e:
            print(f"delete_all_events method: Failed to delete event '{event['summary']}' (from {event_start} to {event_end}): {e}")




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
                # print(f"extract_event_data method: Invalid time format for event '{event_name}' with time '{event_time}'")
                # return []
                continue
    print("extract_event_data method: Gsheet events: \n"+str(event_list))
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
                print("extract_existing_event_data method: reducing by 1 day")
                start_time_obj -= timedelta(days=1)
                end_time_obj -= timedelta(days=1)

            event_list.append({
                'name': event['summary'],
                'start': start_time_obj.strftime('%Y-%m-%dT%H:%M:%S'),
                'end': end_time_obj.strftime('%Y-%m-%dT%H:%M:%S')
            })
        except KeyError:
            print(f"extract_existing_event_data method: Missing start/end time for event '{event['summary']}'")
            continue
    print("extract_existing_event_data method: Gcal events: \n"+str(event_list))
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
    pst_offset = timedelta(hours=-8)# -8 = pst offset, -6    = CST offsets
    event_date_obj = datetime.strptime(str(event_date), '%Y-%m-%d')
    # if event_date_obj.time().hour >= datetime.strptime('00:00:00', '%H:%M:%S').time().hour and \
    #         event_date_obj.time().hour < datetime.strptime('06:00:00', '%H:%M:%S').time().hour:
    #     print("compare_and_sync_events method: reducing event_date by 1 day: between 12-6am > "+event_date_obj.strftime('%Y-%m-%d'))
    #     event_date_obj -= timedelta(days=1)
    event_date = event_date_obj.strftime('%Y-%m-%d')

    # Time range: from midnight on the event_date to 3 AM the next day (all in PST)
    time_min = (datetime.strptime(f"{event_date} 00:00", '%Y-%m-%d %H:%M') - pst_offset).isoformat() + 'Z'
    time_max = (datetime.strptime(f"{event_date} 04:00", '%Y-%m-%d %H:%M') + timedelta(days=1) - pst_offset).isoformat() + 'Z'

    # Get existing events from the calendar
    events_result = service.events().list(calendarId=calendar_id, timeMin=time_min, timeMax=time_max,
                                          singleEvents=True, orderBy='startTime').execute()
    existing_events = events_result.get('items', [])

    # Extract event details for comparison
    new_event_list = extract_event_data(items, event_date, pst_offset)
    existing_event_list = extract_existing_event_data(existing_events,pst_offset)

    # Compare the event lists
    if compare_event_lists(new_event_list, existing_event_list):
        print("compare_and_sync_events method: Changes detected, deleting and re-adding events.")
        delete_all_events(service, event_date, time_min, time_max)
        create_events_from_items( items, event_date)
    else:
        print("compare_and_sync_events method: No changes detected.")



# @socketio.on('gsheets')
def run_pygsheets():
    # global app
    # Authenticate or load the saved token
    global all_values, current_cell, current_day, cells_objs, worksheet, cell_color_modes, worksheet_name, TOKEN_FILE, gsheet_name, gsheet, cell_color_modes, items, mins_diff_to_trigger
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

    # send_notification()

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

            previous_day = (datetime.now() - timedelta(minutes=1440)).strftime("%A")
            # print('previous_day '+previous_day+'curr '+current_day )

            # Execute the clear function only if it's moving from Sunday to Monday
            if previous_day == "Sunday" and current_day == "Monday" and datetime.now().hour == 12 and datetime.now().minute == 1:
                clear_ranges(worksheet, gc, dont_clear_tasks)

            start_row_index, end_row_index, column_index = find_sheet_timerange_indexs(current_time, current_day)
            # move_last_hour_task()
            # fcm_notify_independent()
            # fcm_notify_independent("tet","tesssssst")

            # test notification
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


                # send_notification_notsocket(str(notification_title+notification_text))
                # send_notification_notsocket(prev_task + " completed?")
                refresh_worksheet_buttons_matrix(current_day)

                notification_title = (f"{current_time} - {start_task}")
                notification_text = (
                    f" {prev_task_time} - {prev_task} done?"
                )
                fcm_notify_independent(notification_title,notification_text)

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
    # socketio.run(app, host='0.0.0.0', port=5001, allow_unsafe_werkzeug=True, debug=True)
    app.run(host='0.0.0.0', port=5001)
    print(">>>>>>> Flask HTTP server started ")

