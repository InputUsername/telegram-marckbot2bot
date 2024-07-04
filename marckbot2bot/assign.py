import asyncio
from telegram.ext import CallbackContext
from telegram import Update, Message, Bot
from telegram.constants import ParseMode

import logging
import os
import json
from typing import Callable, Optional

from marckbot2bot.attrdict import AttrDict
from marckbot2bot.db import Connection, do_migrations

DB_PATH = os.path.join(os.getenv('STATE_DIRECTORY', ''), 'defines.db')
DB_URL = os.getenv('DATABASE_URL', 'sqlite://' + DB_PATH)


class AssignHandler:
    def __init__(self, bot_username: str, send_message_function: Callable[[Bot, Message, str], None]):
        self.logger = logging.getLogger(__name__)

        self.bot_username = f'@{bot_username}'
        self.send_message_function = send_message_function

        self.cursor = Connection(DB_URL)

        # self.cursor.execute('CREATE TABLE IF NOT EXISTS defines (name TEXT, chat TEXT, message TEXT)')
        # self.cursor.execute('CREATE TABLE IF NOT EXISTS bonks (user_id TEXT, chat_id TEXT)')

        # self.db.commit()

    async def do_migrations(self, app):
        print('Migrating database')
        await do_migrations(self.cursor)

    def close(self):
        self.logger.info('Exporting database definitions')
        self.db.close()

    async def _add_definition(self, name: str, message: Message, chat: str):
        """Add a definition to the database"""

        self.logger.info(f'Adding database definition {name} for chat {chat}: {message}')

        existing = await self.cursor.select_one('SELECT 1 FROM defines WHERE name=? AND chat=?', (name, chat))
        if existing is None:
            if message.text:
                text = message.text_markdown_v2_urled
                encoded_message = message.to_dict()
                encoded_message['text'] = text
                encoded_message = json.dumps(encoded_message)
            else:
                encoded_message = message.to_json()
            await self.cursor.execute('INSERT INTO defines (name, chat, message) VALUES (?, ?, ?)',
                                (name, chat, encoded_message))

    async def _remove_definition(self, name: str, chat: str):
        """Remove a definition from the database"""

        self.logger.info(f'Removing database definition {name} for chat {chat}')

        await self.cursor.execute('DELETE FROM defines WHERE name=? AND chat=?', (name, chat))

    async def _get_definition(self, name: str, chat: str) -> Optional[Message]:
        """Get a definition Message from the database or None if it doesn't exist"""

        self.logger.info(f'Retrieving database definition {name} for chat {chat}')

        row = await self.cursor.select_one('SELECT message FROM defines WHERE name=? AND chat=?', (name, chat))
        if row is not None:
            return AttrDict(json.loads(row[0]))
        return None

    async def _update_definition(self, name: str, message: Message, chat: str):
        if message.text:
            text = message.text_markdown_v2_urled
            encoded_message = message.to_dict()
            encoded_message['text'] = text
            encoded_message = json.dumps(encoded_message)
        else:
            encoded_message = message.to_json()
        await self.cursor.update_or_insert('defines', {'name': name, 'chat': chat}, {'message': encoded_message})

    async def assign(self, update: Update, context: CallbackContext):
        """Handle the /assign command"""

        try:
            message = update.message

            words = message.text.split()
            if len(words) != 2:
                return

            command_name = words[1]
            await self._add_definition(command_name, message.reply_to_message, message.chat.id)

        except AttributeError as e:
            self.logger.warning(e)

    async def unassign(self, update: Update, context: CallbackContext):
        """Handle the /unassign command"""

        try:
            message = update.message

            words = message.text.split()
            if len(words) != 2:
                return

            command_name = words[1]
            await self._remove_definition(command_name, message.chat.id)

        except AttributeError as e:
            self.logger.warning(e)

    async def reassign(self, update: Update, context: CallbackContext):
        """Handle the /reassign command"""
        try:
            message = update.message

            words = message.text.split()
            if len(words) != 2:
                return

            if not message.reply_to_message:
                return

            command_name = words[1]
            await self._update_definition(command_name, message.reply_to_message, message.chat.id)

        except AttributeError as e:
            self.logger.warning(e)

    async def increase_bonk(self, user_id, chat_id):
        await self.cursor.execute('INSERT INTO bonks (user_id, chat_id) VALUES (?, ?)', (user_id, chat_id))

    async def handle_bonks(self, update: Update, context: CallbackContext):
        chat_id = update.effective_chat.id
        msg = ''
        for user_id, bonks in await self.cursor.select('SELECT user_id, COUNT(user_id) FROM bonks WHERE chat_id=? GROUP BY user_id ORDER BY COUNT(user_id) DESC LIMIT 10', (chat_id,)):
            try:
                user = await context.bot.get_chat_member(chat_id, user_id)
                user_name = user.user.mention_html()
            except:
                user_name = 'unknown user'
            msg += f'<code>{bonks}</code> {user_name}\n'
        if not msg:
            msg = "No bonk counts"
        await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode=ParseMode.HTML, disable_notification=True)

    async def handle_command(self, update: Update, context: CallbackContext):
        """Handle assigned commands"""

        try:
            command_name = context.matches[0].group(1)
            if command_name.endswith(self.bot_username):
                length = len(self.bot_username)
                command_name = command_name[:-length]

            if command_name == 'bonk' and update.message.reply_to_message:
                await self.increase_bonk(update.message.reply_to_message.from_user.id, update.effective_chat.id)

            message = update.message
            chat = message.chat.id

            definition = await self._get_definition(command_name, chat)
            if definition is not None:
                self.logger.info(f'Executing command {command_name} for chat {chat}')
                reply_to = None
                if message.reply_to_message:
                    reply_to = message.reply_to_message.message_id
                await self.send_message_function(context.bot, definition, chat, reply_to=reply_to)

        except AttributeError as e:
            self.logger.warning(e)

    async def defines(self, update: Update, context: CallbackContext):
        """Handle the /defines command"""

        try:
            chat = update.message.chat.id

            defines = []
            current = await self.cursor.select('SELECT name FROM defines WHERE chat=?', (chat,))
            for row in current:
                defines.append(f'/{row[0]}')

            if defines:
                defines = '\n- '.join(defines)
                await context.bot.sendMessage(chat, f'Current defines are:\n- {defines}')
            else:
                await context.bot.sendMessage(chat, 'There are currently no defines.')

        except Exception as e:
            self.logger.warning(e)
