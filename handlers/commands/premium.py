from pyrogram import Client
from pyrogram.types import Message

from utils.logger import logger
from utils.db import db
from config import messages
from handlers.payment.helpers import create_premium_management_keyboard
from handlers.payment.helpers import get_premium_display_info
from utils.decorators import combined_user_check, handle_errors

@combined_user_check
@handle_errors()
async def handle_premium_purchase_command(client: Client, message: Message) -> None:
    """Handles the /premium command directly"""
    user_id = message.from_user.id
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