from pyrogram import Client
from pyrogram.types import Message, ReplyKeyboardRemove
from datetime import datetime

from utils.logger import logger
from utils.db import db
from config import messages
from handlers.payment.helpers import get_plan_name
from handlers.payment.helpers import create_premium_management_keyboard, create_plans_keyboard
from handlers.payment.helpers import get_premium_display_info

async def handle_premium_purchase_command(client: Client, message: Message) -> None:
    """Handles the /premium command directly"""
    try:
        user_id = message.from_user.id
        
        # Check if user is banned
        is_banned, ban_reason = db.is_user_banned(user_id)
        if is_banned:
            logger.warning(f"[🚫] Banned user {user_id} attempted to use /premium command")
            await message.reply_text(messages.USER_BANNED(ban_reason), reply_markup=ReplyKeyboardRemove())
            return
        
        db.add_user(user_id, False)
        logger.info(f"[💲] Received /premium command from user {user_id}")

        status, text, markup = await get_premium_display_info(user_id)
        
        if status is None:
            # Error occurred
            await message.reply_text(text, reply_markup=ReplyKeyboardRemove())
            return
            
        # Override text if not premium to use command text
        if status is False:
            text = messages.PLANS_TEXT_COMMAND

        await message.reply_text(text, reply_markup=markup)

    except Exception as e:
        logger.error(f"[❌] Error handling /premium command for user {message.from_user.id}: {e}")
        await message.reply_text(messages.ERROR_GENERIC, reply_markup=ReplyKeyboardRemove()) 