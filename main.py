import configparser
import os
import re

import aiohttp
import pyrogram
from google.oauth2.service_account import Credentials


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


async def download_file_from_drive(file_id):
    url = f'https://drive.google.com/u/0/uc?id={file_id}&export=download'
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                raise Exception(f'Failed to download file {file_id}')

            content_disposition = response.headers.get('Content-Disposition')
            if content_disposition:
                file_name = re.findall("filename=(.+)", content_disposition)[0].strip('"')
            else:
                file_name = 'unknown'

            with open(file_name, 'wb') as f:
                while True:
                    chunk = await response.content.read(1024)
                    if not chunk:
                        break
                    f.write(chunk)

            return file_name


@app.on_message(pyrogram.filters.command(['upload'], prefixes='/'))
async def handle_upload_command(client, message):
    try:
        # Get the Google Drive link from the message text
        link = message.text.split()[1]

        # Extract the folder ID and file ID from the link
        folder_id = link.split('/')[-2]
        file_id = link.split('/')[-1]

        # Get a list of all file IDs in the folder
        url = f'https://drive.google.com/drive/folders/{folder_id}'
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    raise Exception(f'Failed to get files from folder {folder_id}')

                html_text = await response.text()
                ids = re.findall('/file/d/(.+?)"', html_text)

        # Download the file and upload it to Telegram
        file_name = await download_file_from_drive(file_id)
        caption = os.path.splitext(file_name)[0]
        await client.send_document(chat_id=message.chat.id, document=file_name, caption=caption)

        # Cleanup (optional)
        os.remove(file_name)

        # Loop through all other files in the folder and repeat
        for id in ids:
            if id != file_id:
                file_name = await download_file_from_drive(id)
                caption = os.path.splitext(file_name)[0]
                await client.send_document(chat_id=message.chat.id, document=file_name, caption=caption)

                # Cleanup (optional)
                os.remove(file_name)

    except Exception as e:
        await client.send_message(chat_id=message.chat.id, text=str(e))


@app.on_message(pyrogram.filters.command(['start'], prefixes='/'))
async def handle_start_command(client, message):
    user_name = message.from_user.first_name
    await client.send_message(chat_id=message.chat.id, text=f"Hello {user_name}! Welcome to my bot.")


@app.on_message(pyrogram.filters.command(['help'], prefixes='/'))
async def handle_help_command(client, message):
    help_text = "To use this bot, simply send me a message with a Google Drive link and I will send you back the files in that folder. You can also use the /upload command followed by a Google Drive link to get files from a specific folder.\n\n"
    await client.send_message(chat_id=message.chat.id, text=help_text)


# Start the bot
app.run()
