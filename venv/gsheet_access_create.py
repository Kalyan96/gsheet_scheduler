import pygsheets

# Define the path to the token file
TOKEN_FILE = "gsheet_token.json"

# Perform the initial authentication
gc = pygsheets.authorize()

# Save the authentication token to a file
gc.save_as(TOKEN_FILE)
