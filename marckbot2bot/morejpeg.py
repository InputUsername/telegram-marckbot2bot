from telegram.ext import CallbackContext
from telegram import Update

from PIL import Image

from io import BytesIO

import logging


JPEG_QUALITY = 1


def jpegify(image: Image.Image) -> Image.Image:
    """Round-trip an image through JPEG at the lowest quality Pillow allows"""
    buffer = BytesIO()
    image.convert('RGB').save(buffer, format='JPEG', quality=JPEG_QUALITY)
    buffer.seek(0)
    crushed = Image.open(buffer)
    crushed.load()
    return crushed


def jpegify_sticker(data: bytes) -> bytes:
    """Crush a static (WebP) sticker but keep its transparency, so it still looks like a sticker"""
    original = Image.open(BytesIO(data)).convert('RGBA')
    crushed = jpegify(original).convert('RGBA')
    crushed.putalpha(original.getchannel('A'))
    output = BytesIO()
    crushed.save(output, format='WEBP', quality=80)
    return output.getvalue()


async def more_jpeg(update: Update, context: CallbackContext):
    """Send a photo, image file (document) or static sticker back JPEG-encoded"""

    try:
        bot = context.bot
        message = update.message
        reply = message.reply_to_message

        if reply.sticker:
            if reply.sticker.is_animated or reply.sticker.is_video:
                await message.reply_text('Only static stickers can be jpegged')
                return
            file = await bot.get_file(reply.sticker.file_id)
            sticker = jpegify_sticker(bytes(await file.download_as_bytearray()))
            await bot.send_sticker(chat_id=message.chat.id, sticker=sticker)
            return

        file_id = reply.photo[-1].file_id if reply.photo else reply.document.file_id
        file = await bot.get_file(file_id)
        content = BytesIO(await file.download_as_bytearray())
        image = Image.open(content)

        converted = BytesIO()
        image.save(converted, format='JPEG', quality=JPEG_QUALITY)

        await bot.send_photo(chat_id=message.chat.id, photo=converted.getvalue())
    except AttributeError as e:
        logging.warn(e)
