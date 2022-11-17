#!/usr/bin/env python

import os
import logging
import urllib3
import requests

from telegram import ForceReply, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
    CallbackContext,
)

urllib3.disable_warnings()

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

UPLOAD, DOWNLOAD = range(2)

def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    update.message.reply_markdown_v2(
        fr'Hi {user.mention_markdown_v2()}\!',
        reply_markup=ForceReply(),
    )

def upload(update: Update, context: CallbackContext):
    """Starts the conversation and asks the user for url"""
    update.message.reply_text("Enter your url :- ")

    return UPLOAD


def change_filename(update: Update, context: CallbackContext):
    """Stores the selected url and asks for change file."""
    user = update.message.from_user
    url = update.message.text
    filename = os.path.basename(url)
    context.user_data["url"] = url
    update.message.reply_text(
        f'Default filename is , "{filename[0:60]}", If you want to chnage filename'
        'enter new filename, or send /skip if you don\'t want to.',
    )

    return DOWNLOAD

def downloader(url: str, filename: str):
    download_path = 'downloads'
    if not os.path.isdir(download_path):
        os.mkdir(download_path)

    full_name = os.path.join(download_path, filename)

    with requests.get(url, stream=True, verify=False) as r:
        r.raise_for_status()
        print(full_name)
        with open(full_name, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024): 
                f.write(chunk)
    return full_name

def uploader(filename: str):
    session = requests.session()
    with open(filename, "rb") as fp:
        file = {"file": (filename, fp)}
        resp = session.post('https://api.anonfiles.com/upload', files=file).json()
        if resp['status']:
            urlshort = resp['data']['file']['url']['short']
            urllong = resp['data']['file']['url']['full']
            return f'File uploaded:\nFull URL: {urllong}\nShort URL: {urlshort}'
        else:
            message = resp['error']['message']
            errtype = resp['error']['type']
            return f'[ERROR]: {message}\n{errtype}'

def file_remover(filename: str):
    if os.path.isfile(filename):
        os.remove(filename)
    else:
         print("file not found.")


def download(update: Update, context: CallbackContext):
    """download file and upload file with given name"""
    user = update.message.from_user
    url = context.user_data.get("url", 'Not found')
    filename = update.message.text
    msg = update.message.reply_text("Downloading file...")
    full_name = downloader(url, filename)
    msg.edit_text("File downloaded")
    msg = update.message.reply_text("Uploading file...")
    resp = uploader(full_name)
    file_remover(full_name)
    msg.edit_text(resp)

    return ConversationHandler.END


def skip_download(update: Update, context: CallbackContext):
    """Skip change file name, download and upload file with default name"""
    user = update.message.from_user
    url = context.user_data.get("url", 'Not found')
    filename = os.path.basename(url)
    msg = update.message.reply_text("Downloading file...")
    full_name = downloader(url, filename)
    msg.edit_text("File downloaded")
    msg = update.message.reply_text("Uploading file...")
    resp = uploader(full_name)
    file_remover(full_name)
    msg.edit_text(resp)

    return ConversationHandler.END

def cancel(update: Update, context: CallbackContext) -> int:
    """Cancels and ends the conversation."""
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    update.message.reply_text(
        'Bye! I hope we can talk again some day.'
    )

    return ConversationHandler.END


def main() -> None:
    """Run the bot."""
    updater = Updater("TOKEN")

    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))

    # Add conversation handler with the states UPLOAD and DOWNLOAD
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('upload', upload)],
        states={
            UPLOAD: [MessageHandler(Filters.entity('url'), change_filename)],
            DOWNLOAD: [MessageHandler(Filters.text & ~Filters.command, download), CommandHandler('skip', skip_download)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    dispatcher.add_handler(conv_handler)

    updater.start_polling()

    updater.idle()


if __name__ == '__main__':
    main()