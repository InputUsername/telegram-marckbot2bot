from telegram.ext import CallbackContext
from telegram import Update

from PIL import Image, ImageEnhance

from io import BytesIO

import logging


JPEG_QUALITY = 1
JPEG_ROUNDS = 3
SCALE = 0.8
MIN_SIZE = 16


def jpegify(image: Image.Image) -> Image.Image:
    """Degrade an image so that every pass comes out visibly worse than the last.

    JPEG at quality 1 on its own converges after a single pass, so re-running it
    barely changes anything. Two things keep the decay compounding: contrast,
    colour and sharpness are amplified before each pass, so the previous pass's
    artifacts become part of the picture, and the image keeps only 80% of its
    resolution. Nothing else survives a round trip through Telegram, so the
    dimensions are what remember how many times an image has been jpegged.
    """
    image = image.convert('RGB')
    image = ImageEnhance.Contrast(image).enhance(1.25)
    image = ImageEnhance.Color(image).enhance(1.35)
    image = ImageEnhance.Sharpness(image).enhance(2.0)

    width, height = image.size
    if min(width, height) * SCALE >= MIN_SIZE:
        image = image.resize((int(width * SCALE), int(height * SCALE)), Image.BILINEAR)

    for _ in range(JPEG_ROUNDS):
        buffer = BytesIO()
        image.save(buffer, format='JPEG', quality=JPEG_QUALITY)
        buffer.seek(0)
        image = Image.open(buffer)
        image.load()
    return image


def jpegify_photo(data: bytes) -> bytes:
    """Crush a photo or image document and return it as JPEG"""
    output = BytesIO()
    jpegify(Image.open(BytesIO(data))).save(output, format='JPEG', quality=JPEG_QUALITY)
    return output.getvalue()


def jpegify_sticker(data: bytes) -> bytes:
    """Crush a static (WebP) sticker but keep its transparency, so it still looks like a sticker"""
    original = Image.open(BytesIO(data)).convert('RGBA')
    crushed = jpegify(original).convert('RGBA')
    crushed.putalpha(original.getchannel('A').resize(crushed.size, Image.NEAREST))
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
        photo = jpegify_photo(bytes(await file.download_as_bytearray()))
        await bot.send_photo(chat_id=message.chat.id, photo=photo)
    except AttributeError as e:
        logging.warn(e)
