#!/usr/bin/env python3

from telegram.ext import Updater, CallbackContext, CommandHandler, MessageHandler, Filters
from telegram import Update, Bot, Message, ParseMode

import os
import re
import logging
import signal

import bf

from assign import AssignHandler
from morejpeg import more_jpeg

BOT_USERNAME = 'marckbot2bot'


def error_handler(update: Update, context: CallbackContext):
    logging.warning(f'Error: {context.error} caused by {update}')


def substitute(update: Update, context: CallbackContext):
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

        context.bot.sendMessage(update.message.chat.id, substituted, parse_mode=ParseMode.MARKDOWN_V2)
    except AttributeError as e:
        logging.warning(e)


def send_define_message(bot: Bot, message: Message, chat: str, reply_to: int = None):
    """Send a message that was /assign'ed and stored in the database"""

    reply_to_message_id = {}
    if reply_to is not None:
        reply_to_message_id = {"reply_to_message_id": reply_to}

    if message.text:
        bot.sendMessage(chat, message.text, parse_mode=ParseMode.MARKDOWN_V2, **reply_to_message_id)
    elif message.audio:
        bot.sendAudio(chat, message.audio.file_id, **reply_to_message_id)
    elif message.sticker:
        bot.sendSticker(chat, message.sticker.file_id, **reply_to_message_id)
    else:
        caption = message.caption
        if message.document:
            bot.sendDocument(chat, message.document.file_id, caption=caption, **reply_to_message_id)
        elif message.photo:
            bot.sendPhoto(chat, message.photo[0].file_id, caption=caption, **reply_to_message_id)
        elif message.video:
            bot.sendVideo(chat, message.video.file_id, caption=caption, **reply_to_message_id)
        elif message.voice:
            bot.sendVoice(chat, message.voice.file_id, caption=caption, **reply_to_message_id)

def run_brainfuck(update: Update, context: CallbackContext):
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
        update.message.reply_text("Reply /bf to a message containing brainfuck, an argument to the command will be used as stdin. You can also do /bf <code> to run this code directly.")
    
    out = bf.execute(code, inp)
    if out:
        update.message.reply_text(out)

def main():
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    updater = Updater(token=os.environ['TG_TOKEN'], use_context=True)
    dispatcher = updater.dispatcher

    dispatcher.add_error_handler(error_handler)

    assign_handler = AssignHandler(BOT_USERNAME, send_define_message)

    dispatcher.add_handler(CommandHandler('assign', assign_handler.assign))
    dispatcher.add_handler(CommandHandler('unassign', assign_handler.unassign))
    dispatcher.add_handler(CommandHandler('reassign', assign_handler.reassign))
    dispatcher.add_handler(CommandHandler('defines', assign_handler.defines))
    dispatcher.add_handler(CommandHandler('bonks', assign_handler.handle_bonks))
    dispatcher.add_handler(CommandHandler('bf', run_brainfuck))
    dispatcher.add_handler(CommandHandler('morejpeg', more_jpeg))
    dispatcher.add_handler(MessageHandler(Filters.regex(r'^s([^\\\n])(.*)\1(.*)\1([fiImM]+)?$'), substitute))
    dispatcher.add_handler(MessageHandler(Filters.regex(r'^/([\S]+)$'), assign_handler.handle_command))

    def stop(_signal, _frame):
        logging.info('Received SIGINT, shutting down')
        assign_handler.close()
        updater.stop()

    signal.signal(signal.SIGINT, stop)

    updater.start_polling()


if __name__ == '__main__':
    main()
