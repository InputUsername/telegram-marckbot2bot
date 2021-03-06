from telegram.ext import CallbackContext
from telegram import Update

from PIL import Image

from io import BytesIO

import logging


def more_jpeg(update: Update, context: CallbackContext):
    """Send a photo or image file (document) back JPEG-encoded"""

    try:
        bot = context.bot
        message = update.message
        reply = message.reply_to_message

        file_id = reply.photo[-1].file_id if reply.photo else reply.document.file_id
        content = bot.getFile(file_id)
        image = Image.open(BytesIO(content))

        converted = BytesIO()
        image.save(converted, format='JPEG', quality=1)

        bot.sendPhoto(converted.getvalue(), message.chat.id)
    except AttributeError as e:
        logging.warn(e)
