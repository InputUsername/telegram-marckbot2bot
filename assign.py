from telegram.ext import CallbackContext
from telegram import Update, Message, Bot, ParseMode

import jsonpickle

import sqlite3
import logging
import os
from typing import Callable, Optional

DB_PATH = os.path.join(os.getenv('STATE_DIRECTORY', ''), 'defines.db')


class AssignHandler:
    def __init__(self, bot_username: str, send_message_function: Callable[[Bot, Message, str], None]):
        self.logger = logging.getLogger(__name__)

        self.bot_username = f'@{bot_username}'
        self.send_message_function = send_message_function

        self.db = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.cursor = self.db.cursor()

        self.cursor.execute('CREATE TABLE IF NOT EXISTS defines (name TEXT, chat TEXT, message TEXT)')
        self.cursor.execute('CREATE TABLE IF NOT EXISTS bonks (user_id TEXT, chat_id TEXT)')

        self.db.commit()

    def close(self):
        self.logger.info('Exporting database definitions')
        self.db.close()

    def _add_definition(self, name: str, message: Message, chat: str):
        """Add a definition to the database"""

        self.logger.info(f'Adding database definition {name} for chat {chat}: {message}')

        existing = self.cursor.execute('SELECT 1 FROM defines WHERE name=? AND chat=?', (name, chat)).fetchone()
        if existing is None:
            if message.text:
                message.text = message.text_markdown_v2_urled
            encoded_message = jsonpickle.encode(message)
            self.cursor.execute('INSERT INTO defines (name, chat, message) VALUES (?, ?, ?)',
                                (name, chat, encoded_message))
            self.db.commit()

    def _remove_definition(self, name: str, chat: str):
        """Remove a definition from the database"""

        self.logger.info(f'Removing database definition {name} for chat {chat}')

        self.cursor.execute('DELETE FROM defines WHERE name=? AND chat=?', (name, chat))
        self.db.commit()

    def _get_definition(self, name: str, chat: str) -> Optional[Message]:
        """Get a definition Message from the database or None if it doesn't exist"""

        self.logger.info(f'Retrieving database definition {name} for chat {chat}')

        row = self.cursor.execute('SELECT message FROM defines WHERE name=? AND chat=?', (name, chat)).fetchone()
        if row is not None:
            return jsonpickle.decode(row[0])
        return None

    def assign(self, update: Update, context: CallbackContext):
        """Handle the /assign command"""

        try:
            message = update.message

            words = message.text.split()
            if len(words) != 2:
                return

            command_name = words[1]
            self._add_definition(command_name, message.reply_to_message, message.chat.id)

        except AttributeError as e:
            self.logger.warning(e)

    def unassign(self, update: Update, context: CallbackContext):
        """Handle the /unassign command"""

        try:
            message = update.message

            words = message.text.split()
            if len(words) != 2:
                return

            command_name = words[1]
            self._remove_definition(command_name, message.chat.id)

        except AttributeError as e:
            self.logger.warning(e)
    def reassign(self, update: Update, context: CallbackContext):
        """Handle the /reassign command"""
        try:
            message = update.message

            words = message.text.split()
            if len(words) != 2:
                return

            if not message.reply_to_message:
                return

            command_name = words[1]
            self._remove_definition(command_name, message.chat.id)
            self._add_definition(command_name, message.reply_to_message, message.chat.id)

        except AttributeError as e:
            self.logger.warning(e)

    def increase_bonk(self, user_id, chat_id):
        self.cursor.execute('INSERT INTO bonks (user_id, chat_id) VALUES (?, ?)', (user_id, chat_id))
        self.db.commit()

    def handle_bonks(self, update: Update, context: CallbackContext):
        chat_id = update.effective_chat.id
        msg = ''
        for user_id, bonks in self.cursor.execute('SELECT user_id, COUNT(user_id) FROM bonks WHERE chat_id=? GROUP BY user_id ORDER BY COUNT(user_id) DESC LIMIT 10', (chat_id,)):
            try:
                user = context.bot.get_chat_member(chat_id, user_id)
                user_name = user.user.mention_html()
            except:
                user_name = 'unknown user'
            msg += f'<code>{bonks}</code> {user_name}\n'
        if not msg:
            msg = "No bonk counts"
        context.bot.send_message(chat_id=chat_id, text=msg, parse_mode=ParseMode.HTML, disable_notification=True)

    def handle_command(self, update: Update, context: CallbackContext):
        """Handle assigned commands"""

        try:
            command_name = context.matches[0].group(1)
            if command_name.endswith(self.bot_username):
                length = len(self.bot_username)
                command_name = command_name[:-length]

            if command_name == 'bonk' and update.message.reply_to_message:
                self.increase_bonk(update.message.reply_to_message.from_user.id, update.effective_chat.id)

            message = update.message
            chat = message.chat.id

            definition = self._get_definition(command_name, chat)
            if definition is not None:
                reply_to = None
                if message.reply_to_message:
                    reply_to = message.reply_to_message.message_id
                self.send_message_function(context.bot, definition, chat, reply_to=reply_to)

        except AttributeError as e:
            self.logger.warning(e)

    def defines(self, update: Update, context: CallbackContext):
        """Handle the /defines command"""

        try:
            chat = update.message.chat.id

            defines = []
            current = self.cursor.execute('SELECT name FROM defines WHERE chat=?', (chat,)).fetchone()
            while current is not None:
                defines.append(f'/{current[0]}')
                current = self.cursor.fetchone()

            if defines:
                defines = '\n- '.join(defines)
                context.bot.sendMessage(chat, f'Current defines are:\n- {defines}')
            else:
                context.bot.sendMessage(chat, 'There are currently no defines.')

        except Exception as e:
            self.logger.warning(e)
