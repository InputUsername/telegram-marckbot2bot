from telegram.ext import CallbackContext
from telegram import Update

from PIL import Image

from io import BytesIO

import logging


async def more_jpeg(update: Update, context: CallbackContext):
    """Send a photo or image file (document) back JPEG-encoded"""

    try:
        bot = context.bot
        message = update.message
        reply = message.reply_to_message

        file_id = reply.photo[-1].file_id if reply.photo else reply.document.file_id
        file = await bot.get_file(file_id)
        content = BytesIO(await file.download_as_bytearray())
        image = Image.open(content)

        converted = BytesIO()
        image.save(converted, format='JPEG', quality=1)

        await bot.send_photo(chat_id=message.chat.id, photo=converted.getvalue())
    except AttributeError as e:
        logging.warn(e)
