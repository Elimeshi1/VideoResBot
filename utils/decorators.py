"""
Decorators and common utility functions for the bot.

This module provides decorators for common operations like:
- User ban checking
- User database registration
- Error handling
"""

from functools import wraps
from pyrogram import Client
from pyrogram.types import Message, CallbackQuery
from utils.logger import logger
from utils.db import db
from config import messages


def check_user_ban(func):
    """
    Decorator to check if user is banned before executing the function.
    Works with both Message and CallbackQuery handlers.
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract client and message/callback from args
        if len(args) >= 2:
            client = args[0] if isinstance(args[0], Client) else None
            message_or_callback = args[1]
            
            if isinstance(message_or_callback, (Message, CallbackQuery)):
                user_id = message_or_callback.from_user.id
                user_name = message_or_callback.from_user.first_name or "Unknown"
                
                # Check if user is banned
                is_banned, ban_reason = db.is_user_banned(user_id)
                if is_banned:
                    logger.warning(f"[🚫] Banned user {user_id} ({user_name}) attempted to use function {func.__name__}")
                    
                    # Handle response based on type
                    if isinstance(message_or_callback, Message):
                        await message_or_callback.reply_text(messages.USER_BANNED(ban_reason))
                    elif isinstance(message_or_callback, CallbackQuery):
                        await message_or_callback.answer(f"You are banned. Reason: {ban_reason}", show_alert=True)
                    return
        
        # If not banned, execute the original function
        return await func(*args, **kwargs)
    
    return wrapper


def auto_register_user(func):
    """
    Decorator to automatically register user in database if not exists.
    Works with both Message and CallbackQuery handlers.
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract message/callback from args
        if len(args) >= 2:
            message_or_callback = args[1]
            
            if isinstance(message_or_callback, (Message, CallbackQuery)):
                user_id = message_or_callback.from_user.id
                
                # Add user to database if not exists
                db.add_user(user_id, False)
        
        # Execute the original function
        return await func(*args, **kwargs)
    
    return wrapper


def combined_user_check(func):
    """
    Combined decorator that checks for ban and auto-registers user.
    This is the most commonly used combination.
    """
    @wraps(func)
    @check_user_ban
    @auto_register_user
    async def wrapper(*args, **kwargs):
        return await func(*args, **kwargs)
    
    return wrapper


def handle_errors(error_message: str = None):
    """
    Decorator to handle common errors and send appropriate error messages.
    
    Args:
        error_message: Custom error message to send to user. If None, uses generic error.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.error(f"[❌] Error in {func.__name__}: {e}")
                
                # Try to send error message to user
                if len(args) >= 2:
                    message_or_callback = args[1]
                    error_text = error_message or messages.ERROR_GENERIC
                    
                    try:
                        if isinstance(message_or_callback, Message):
                            await message_or_callback.reply_text(error_text)
                        elif isinstance(message_or_callback, CallbackQuery):
                            if message_or_callback.message:
                                await message_or_callback.message.edit_text(error_text)
                            else:
                                await message_or_callback.answer(error_text, show_alert=True)
                    except Exception as send_error:
                        logger.error(f"[❌] Failed to send error message: {send_error}")
                
                return None
        
        return wrapper
    return decorator


# Common utility functions that were duplicated across files

def get_plan_name(channels: int) -> str:
    """Returns the plan name based on the number of channels."""
    if channels >= 5:
        return "Premium Pro"
    elif channels >= 3:
        return "Premium+"
    elif channels >= 1:
        return "Premium Basic"
    else:
        return "Unknown Plan"


async def send_error_message(message_or_callback, error_text: str) -> None:
    """
    Send error message to user - works with both Message and CallbackQuery.
    Centralized error sending function.
    """
    try:
        formatted_error = f"❌ **ERROR** ❌\n\n{error_text}"
        
        if isinstance(message_or_callback, Message):
            await message_or_callback.reply_text(formatted_error)
        elif isinstance(message_or_callback, CallbackQuery):
            if message_or_callback.message:
                await message_or_callback.message.edit_text(formatted_error)
            else:
                await message_or_callback.answer(formatted_error, show_alert=True)
                
    except Exception as e:
        logger.error(f"[❌] Error sending error message: {e}")
