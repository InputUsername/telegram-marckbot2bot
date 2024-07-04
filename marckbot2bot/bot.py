#!/usr/bin/env python3

from telegram.ext import ApplicationBuilder, CallbackContext, CommandHandler, MessageHandler, filters
from telegram import Update, Bot, Message
from telegram.constants import ParseMode

import os
import re
import logging
import signal

import marckbot2bot.bf as bf
from marckbot2bot.assign import AssignHandler
from marckbot2bot.morejpeg import more_jpeg

BOT_USERNAME = 'marckbot2bot'


async def error_handler(update: Update, context: CallbackContext):
    logging.warning(f'Error: {context.error} caused by {update}')


async def substitute(update: Update, context: CallbackContext):
    try:
        match = context.matches[0].group(2)
        replace = context.matches[0].group(3)
        flags = context.matches[0].group(4) or ''
        useflags = 0
        count = 0

        logging.debug('match: %s - replace: %s', match, replace)

        if 'f' in flags.lower():
            # Only replace first
            count = 1
        if 'i' in flags.lower():
            useflags = re.IGNORECASE
        if 'm' in flags.lower():
            useflags |= re.MULTILINE

        if match == '.*':
            count = 1

        substituted = re.sub(match, replace, update.message.reply_to_message.text_markdown_v2_urled, count=count, flags=useflags)

        await context.bot.sendMessage(update.message.chat.id, substituted, parse_mode=ParseMode.MARKDOWN_V2)
    except AttributeError as e:
        logging.warning(e)


async def send_define_message(bot: Bot, message: Message, chat: str, reply_to: int = None):
    """Send a message that was /assign'ed and stored in the database"""

    reply_to_message_id = {}
    if reply_to is not None:
        reply_to_message_id = {"reply_to_message_id": reply_to}

    if "text" in message and message.text:
        await bot.sendMessage(chat, message.text, parse_mode=ParseMode.MARKDOWN_V2, **reply_to_message_id)
    elif "audio" in message and message.audio:
        await bot.sendAudio(chat, message.audio["file_id"], **reply_to_message_id)
    elif "sticker" in message and message.sticker:
        await bot.sendSticker(chat, message.sticker["file_id"], **reply_to_message_id)
    else:
        caption = message.get("caption", "")
        if message.document:
            await bot.sendDocument(chat, message.document["file_id"], caption=caption, **reply_to_message_id)
        elif message.photo:
            await bot.sendPhoto(chat, message.photo[0]['file_id'], caption=caption, **reply_to_message_id)
        elif message.video:
            await bot.sendVideo(chat, message.video["file_id"], caption=caption, **reply_to_message_id)
        elif message.voice:
            await bot.sendVoice(chat, message.voice["file_id"], caption=caption, **reply_to_message_id)

async def run_brainfuck(update: Update, context: CallbackContext):
    if update.message.reply_to_message:
        code = update.message.reply_to_message.text
        try:
            inp = update.message.text.split(None, 1)[1]
        except IndexError:
            inp = ""
    else:
        try:
            code = update.message.text.split(None, 1)[1]
            inp = ""
        except IndexError:
            code = False

    if not code:
        await update.message.reply_text("Reply /bf to a message containing brainfuck, an argument to the command will be used as stdin. You can also do /bf <code> to run this code directly.")
        return

    out = bf.execute(code, inp)
    if out:
        await update.message.reply_text(out)

def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    application = ApplicationBuilder().token(os.environ['TG_TOKEN']).build()

    application.add_error_handler(error_handler)

    assign_handler = AssignHandler(BOT_USERNAME, send_define_message)

    application.add_handler(CommandHandler('assign', assign_handler.assign))
    application.add_handler(CommandHandler('unassign', assign_handler.unassign))
    application.add_handler(CommandHandler('reassign', assign_handler.reassign))
    application.add_handler(CommandHandler('defines', assign_handler.defines))
    application.add_handler(CommandHandler('bonks', assign_handler.handle_bonks))
    application.add_handler(CommandHandler('bf', run_brainfuck))
    application.add_handler(CommandHandler('morejpeg', more_jpeg))
    application.add_handler(MessageHandler(filters.Regex(r'^s([^\\\n])(.*)\1(.*)\1([fiImM]+)?$'), substitute))
    application.add_handler(MessageHandler(filters.Regex(r'^/([\S]+)$'), assign_handler.handle_command))

    def stop(_signal, _frame):
        logging.info('Received SIGINT, shutting down')
        assign_handler.close()
        application.stop()

    signal.signal(signal.SIGINT, stop)

    webhook_url = os.getenv('WEBHOOK_URL', None)
    if webhook_url is not None:
        application.run_webhook(
            listen="0.0.0.0",
            port=os.environ['PORT'],
            url_path=os.environ['URL_PATH'],
            webhook_url=webhook_url,
            secret_token=os.environ['SECRET_TOKEN'],
        )
    else:
        application.run_polling()


if __name__ == '__main__':
    main()
