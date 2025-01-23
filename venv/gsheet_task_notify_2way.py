import time


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



logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Replace 'YOUR_BOT_TOKEN' with your actual bot token

bot_state = {
    'token': '6359135166:AAES3zb5uvg30FDYe2wDUs6T0eL4qnVbkEE',
    'chat_id': '6020027159',
    'current_option': None,  # Store the currently selected option
    'updater': None,
    'dispatcher': None,
    'response_rx':False,
    'message_timeout':3400# 58 mins
}

current_cell = {
    'row_index':None,
    'col_index':None
}

bot_state['token'] = '6359135166:AAES3zb5uvg30FDYe2wDUs6T0eL4qnVbkEE'
bot_state['chat_id'] = "6020027159"

gsheet_name = 'gsheet-python'
# worksheet_name = 'testtimetable'#test sheet
worksheet_name = 'Timetable'#orignal sheet


cell_color_modes={
    'current_CELL_COLOR':(0.20392157, 1, 0.20392157, 0),#light green
    'unused_CELL_COLOR' : (1, 1, 1, .3),#white
    'done_CELL_COLOR' : (0.6, 0.6, 0.9, .3),#light blue
    'not_done_CELL_COLOR' : (0.8, 0.4, 0.4, .3)#light red
}

# Define the path to the token file
TOKEN_FILE = "sheets-python-integrate-587cd0e2df13.json"

# TOKEN_FILE = "gsheet_token_serviceacc_key.json"
# Function to authenticate with Google Sheets
def authenticate():
    try:
        # Try to load the token from the file
        gc = pygsheets.authorize(service_file =TOKEN_FILE)
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


def number_to_letter_notation(column_int):
    start_index = 1  # it can start either at 0 or at 1
    letter = ''
    while column_int > 25 + start_index:
        letter += chr(65 + int((column_int - start_index) / 26) - 1)
        column_int = column_int - (int((column_int - start_index) / 26)) * 26
    letter += chr(65 - start_index + (int(column_int)))

def refresh_worksheet_matrix():
    global all_values, cells_objs, worksheet
    all_values = worksheet.get_all_values()
    cells_objs = worksheet.get_all_values(returnas='cell', include_tailing_empty=False, include_tailing_empty_rows=False)

#----------------------------------------------- telegram methods -----

def text_message_handler(update, context):
    global bot_state, current_cell, all_values, cell_color_modes
    try :
        print("DEBUG:text_message_handler method")
        message_text = update.message.text
        change_cell_background_color(current_cell['worksheet'], current_cell['row_index']-1, current_cell['col_index'], cell_color_modes['not_done_CELL_COLOR'])
        current_cell['worksheet'].update_value( xlsxwriter.utility.xl_rowcol_to_cell_fast(current_cell['row_index']-1,current_cell['col_index']+1) , message_text)
        # query.edit_message_text(text="Task marked as not done! other task added")
        refresh_worksheet_matrix()
        print("Current task at "+all_values[current_cell['row_index']][0] +" "+ all_values[0][ current_cell['col_index'] ]+ " marked not done, '"+ message_text +"' task added in adjacent col ")
        bot_state['response_rx'] = False
    except Exception as e:
        logger.error("Error during text_message_handler method: %s", str(e))
        error_intimate_message("Error during text_message_handler method: %s"+str(e))
        # telegram_bot_init()



def button_callback(update, context):
    global bot_state, current_cell, cell_color_modes
    try:
        print("DEBUG:Button_callback method")
        query = update.callback_query
        if query.message.text: # this part is to extract the time message was sent and
            related_msg = str(query.message.text)
            related_msg_time = related_msg.splitlines()[0].split(" ")[0] + " " + related_msg.splitlines()[0].split(" ")[1]
            related_msg_day = related_msg.splitlines()[0].split(" ")[2]
            start_row_index, end_row_index, column_index = find_sheet_timerange_indexs(related_msg_time, related_msg_day)
        query.answer()
        print ("Button : '"+query.data+"' pressed for the msg '"+str(related_msg)+"' at "+related_msg_day+"  "+related_msg_time+" !")
        message = "You pressed: " + query.data
        query.edit_message_text(text=message)
        bot_state['response_rx'] = True
        if query.data == "done":
            change_cell_background_color(current_cell['worksheet'], start_row_index, column_index, cell_color_modes['done_CELL_COLOR'])
            query.edit_message_text(text=str(all_values[start_row_index][column_index])+" Task marked as done!")
            bot_state['response_rx'] = False
        elif query.data == "not done":
            change_cell_background_color(current_cell['worksheet'], start_row_index, column_index, cell_color_modes['not_done_CELL_COLOR'])
            query.edit_message_text(text=str(all_values[start_row_index][column_index])+" Task marked as not done!")
            bot_state['response_rx'] = False
        elif query.data == "extend":
            change_cell_background_color(current_cell['worksheet'], start_row_index, column_index, cell_color_modes['done_CELL_COLOR'])
            query.edit_message_text(text=str(all_values[start_row_index][column_index])+" after this task, will be extended!")
            # function code pending ...
            bot_state['response_rx'] = False
        elif query.data == "later":
            change_cell_background_color(current_cell['worksheet'], start_row_index, column_index, cell_color_modes['not_done_CELL_COLOR'])
            query.edit_message_text(text=str(all_values[start_row_index][column_index])+" Task will be moved to later tasks!")
            # function code pending ...
            bot_state['response_rx'] = False


    except Exception as e:
        logger.error("Error during button callback method: %s", str(e))
        error_intimate_message("Error during button callback method: %s"+str(e))
        # telegram_bot_init()




try:
    # Callback function when a button is pressed
    button_handler = CallbackQueryHandler(button_callback)
except Exception as e:
    logger.error("Error during button_handler callback: %s", str(e))
    error_intimate_message("Error during button_handler callback: %s" + str(e))
    # telegram_bot_init()


# Add a handler for button callbacks
def test_command(update, context):
    try:
        send_message_with_buttons(update, context, "This is a test message with buttons:", ["Option 1", "Option 2", "Option 3"])
    except Exception as e:
        logger.error("Error during test_command method: %s", str(e))
        error_intimate_message("Error during test_command method: %s"+str(e))
        # telegram_bot_init()

def send_message( message):
    global bot_state
    try:
        # bot = Bot(token=bot_state['token'])
        bot_state['bot'].send_message(chat_id=bot_state['chat_id'], text=message)
    except Exception as e:
        logger.error("Error during telegram send message: %s", str(e))
        error_intimate_message("Error during telegram send message method: %s" + str(e))
        # telegram_bot_init()

# Define a command handler to trigger the test message
def send_message_with_buttons(update, context, message, buttons):
    global bot_state
    try:
        user_id = bot_state['chat_id']
        keyboard = [[InlineKeyboardButton(button, callback_data=button)] for button in buttons]
        reply_markup = InlineKeyboardMarkup(keyboard)
        # bot = Bot(token=bot_state['token'])
        bot_state['bot'].send_message(chat_id=bot_state['chat_id'], text=message, reply_markup=reply_markup)

        # Schedule a job to delete the message after a timeout
        # context.job_queue.run_once(delete_message, bot_state['message_timeout'], context=user_id)

    except Exception as e:
        logger.error("Error during send_message_with_buttons method: %s", str(e))
        error_intimate_message("Error during send_message_with_buttons method: %s" + str(e))
        # telegram_bot_init()

# Define a function to delete the message after a timeout
def delete_message(context):
    job = context.job
    user_id = job.context

    try:
        # Delete the message sent by the bot
        context.bot.delete_message(chat_id=user_id, message_id=job.message.message_id)
    except Exception as e:
        logger.error("Error during message deletion: %s", str(e))
        error_intimate_message("Error during message deletion: %s" + str(e))

def error_intimate_message(message):
    global bot_state
    try:
        # bot = Bot(token=bot_state['token'])
        bot_state['bot'].send_message(chat_id=bot_state['chat_id'], text=message)
    except Exception as e:
        logger.error("Error during error_intimate_message: %s", str(e))




def telegram_bot_init():
    global bot_state
    while True:
        try:
            print("DEBUG: telegram_bot_init method")
            # Initialize the updater and dispatcher
            bot_state['bot'] = Bot(token=bot_state['token'])
            bot_state['updater'] = Updater(token=bot_state['token'], use_context=True)
            bot_state['dp'] = bot_state['updater'].dispatcher  # Define the dispatcher

            bot_state['dp'].add_handler(button_handler)  # Add the button handler
            bot_state['dp'].add_handler(MessageHandler(Filters.text & ~Filters.command, text_message_handler)) # Add the text message handler

            # bot_state['dp'].add_handler(CommandHandler("test", test_command))  # Add the test command handler

            # test_command(None, bot_state['updater'])
            # Send the initial message with inline keyboard buttons
            # send_initial_message(None, bot_state['updater'])

            # # Start the bot
            bot_state['updater'].start_polling(poll_interval=1.0, timeout=10)
            time.sleep(599)
            print("DEBUG: telegram_bot_init method: graceful reset")
            bot_state['updater'].stop()
            bot_state['bot'].close()
            # print("DEBUG: telegram_bot_init method end")
            # bot_state['updater'].idle()
        except Exception as e:
            logger.error("Error during telegram_bot_init method: %s", str(e))
            error_intimate_message("Error during telegram_bot_init method: %s" + str(e))


#----------------------------------------------- telegram methods =====


# Authenticate or load the saved token
gc = authenticate()

# Open the Google Sheet
# gsheet = gc.open(gsheet_name)
gsheet = gc.open_by_key("1XyG8MYwwpCvWg-yvCjS8uu2Ra93uIGIc2K3_qMGlEyY")

worksheet_name = worksheet_name

# Create a thread to run the bot
bot_thread = threading.Thread(target=telegram_bot_init)
# Start the telegram thread
bot_thread.start()


# print(all_values)
past_min = datetime.now().minute - 1

while True :
    try:
        current_min = datetime.now().minute
        if current_min != past_min:#hour changed, execute the while syntax after it
            past_min = current_min
            print("iteration :------------------->>")
        else : # hour didnt change
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
        refresh_worksheet_matrix()

        start_row_index, end_row_index, column_index = find_sheet_timerange_indexs(current_time, current_day)



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
            prev_task = all_values[current_cell['row_index']-1][current_cell['col_index']]
            prev_task_time = (datetime.strptime(current_time, "%I:%M %p")-timedelta(hours=1, minutes=0)).strftime("%I:%M %p")
            print("Current task :",start_task)
            print("Upcoming task :",end_task)


            #update the cell colors every hour
            hour_change_cell_color_update(current_cell['worksheet'], current_cell['row_index'], current_cell['col_index'])

            send_message( "Current task : "+start_task+"\n | Upcoming task :"+end_task+"\n | Current dateime: "+current_time+" "+current_day)
            send_message_with_buttons(None, bot_state['updater'], prev_task_time+" "+current_day+"\n"+"Previous task : "+prev_task+" done?", ["done", "not done", "extend", "later"])

            # notification_title = "Current Tasks"
            # notification_text = (
            #     f"{current_day}, {current_time} - {end_task}: {start_task}"
            # )
            # notification.notify(
            #     title=notification_title,
            #     message=notification_text,
            #     app_name="Timetable Reminder",
            # )
        elif (start_row_index is not None and end_row_index is not None and column_index is not None):
            curr_task = all_values[start_row_index][column_index]
            print("Same task as before "+curr_task)
        else:
            print("No tasks found at the current time.")
            print("Its sleep time ! zzZ")
    except Exception as e:
        logger.error("Error during main method: %s", str(e))
        error_intimate_message("Error during main method: %s" + str(e))




'''
pending tasks :
- when the button is sent and no response sent for >10mins, getting "" error and further button clicks not working 

pending improvements :
- when extend is pressed, need to move non-essential tasks until EOD. if 'chill' task is there while shifting, then delete it 
- when later is pressed, add the task to a later list in the chart 
- in the button-callback, include timestamp in the message while sending message, so that during button callback, the repsective task can be tracked and marked in the sheet accordingly 
- when we move past 12am sunday, the values are taken from different column since day name has changed, for all others its managed , find a way for that :/
- when we reply with a task name, it should have a text box along with buttons attached to each message

'''