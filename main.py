import pyrogram
import configparser
from google.oauth2.service_account import Credentials
import requests

# Load configuration from config.ini file
config = configparser.ConfigParser()
config.read('config.ini')

# Get Pyrogram settings from the configuration file
api_id = int(config['pyrogram']['api_id'])
api_hash = config['pyrogram']['api_hash'])
bot_token = config['pyrogram']['bot_token'])

# Get Google Drive settings from the configuration file
service_account_file = config['gdrive']['service_account_file']

# Authentication using Google Service Account JSON
creds = Credentials.from_service_account_file(service_account_file)

# Initialize Pyrogram client
app = pyrogram.Client('my_bot', api_id=api_id, api_hash=api_hash, bot_token=bot_token)

# Function to download file from Google Drive
def download_file_from_drive(file_id):
    url = 'https://drive.google.com/u/0/uc?id={}&export=download'.format(file_id)
    session = requests.Session()
    response = session.get(url, stream=True)
    
    # Get the file name from the response headers
    file_name = ''
    if 'Content-Disposition' in response.headers:
        file_name = re.findall("filename=(.+)", response.headers['Content-Disposition'])[0].strip('"')
    else:
        file_name = 'unknown'
    
    # Download the file
    with open(file_name, 'wb') as f:
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)
                
    return file_name

# Handler function for /upload command
def handle_upload_command(client, message):
    # Get the Google Drive link from the message text
    link = message.text.split()[1]
    
    # Extract the folder ID and file ID from the link
    folder_id = link.split('/')[-2]
    file_id = link.split('/')[-1]
    
    # Get a list of all file IDs in the folder
    url = 'https://drive.google.com/drive/folders/{}'.format(folder_id)
    session = requests.Session()
    response = session.get(url)
    html_text = response.text
    ids = re.findall('/file/d/(.+?)"', html_text)
    
    # Download the file and upload it to Telegram
    file_name = download_file_from_drive(file_id)
    client.send_document(chat_id=message.chat.id, document=file_name, caption=file_name)
    
    # Cleanup (optional)
    os.remove(file_name)
    
    # Loop through all other files in the folder and repeat
    for id in ids:
        if id != file_id:
            file_name = download_file_from_drive(id)
            client.send_document(chat_id=message.chat.id, document=file_name, caption=file_name)
            
            # Cleanup (optional)
            os.remove(file_name)

# Handler function for /start command
def handle_start_command(client, message):
    user_name = message.from_user.first_name
    client.send_message(chat_id=message.chat.id, text=f"Hello {user_name}! Welcome to my bot.")

# Handler function for /help command
def handle_help_command(client, message):
    help_text = "To use this bot, simply send me a message with a Google Drive link and I will send you back the files in that folder. You can also use the /upload command followed by a Google Drive link to get files from a specific folder.\n\n"
    client.send_message(chat_id=message.chat.id, text=help_text)

# Register handler functions for /start and /help commands
app.on_message(pyrogram.filters.command(['start'], prefixes='/'), handle_start_command)
app.on_message(pyrogram.filters.command(['help'], prefixes='/'), handle_help_command)

# Register handler function for /upload command
app.on_message(pyrogram.filters.command(['upload'], prefixes='/'), handle_upload_command)

# Start the bot
app.run()
