"""Handlers related to adding, selecting, and removing channels"""

from pyrogram import Client, types
from pyrogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, KeyboardButtonRequestChat,
    ReplyKeyboardRemove, CallbackQuery
)
from datetime import datetime

from utils.logger import logger
from utils.db import db
from .helpers import send_error
from config import messages

async def handle_add_channel_button(client: Client, callback_query: CallbackQuery) -> None:
    """Handle the Add Channel button press (Shows channel selection prompt)"""
    try:
        await callback_query.answer()
        user_id = callback_query.from_user.id
        
        if not db.is_user_premium(user_id):
            await send_error(callback_query.message, messages.ERROR_NOT_PREMIUM)
            return
        
        channels = db.get_user_channels(user_id)
        max_channels = db.get_max_channels(user_id)
        current_channels = len(channels)
        
        if current_channels >= max_channels:
            limit_text = messages.channel_limit_reached_text(current_channels, max_channels)
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(messages.BUTTON_UPGRADE_PLAN, callback_data="upgrade_premium")], 
                [InlineKeyboardButton(messages.BUTTON_BACK_TO_MENU, callback_data="premium_menu")]
            ])
            await callback_query.message.edit_text(limit_text, reply_markup=keyboard)
            logger.info(f"[⚠️] User {user_id} reached channel limit ({current_channels}/{max_channels}) when trying to add.")
            return
        
        request_chat_button = KeyboardButtonRequestChat(
            button_id=1, 
            chat_is_channel=True,
        )
        keyboard = ReplyKeyboardMarkup(
            [
                [KeyboardButton(text=messages.BUTTON_SELECT_CHANNEL, request_chat=request_chat_button)]
            ],
            is_persistent=True,
            resize_keyboard=True,
            one_time_keyboard=True
        )
        info_text = messages.add_channel_prompt_text(current_channels, max_channels)
        
        # Need to send a new message for ReplyKeyboardMarkup
        await callback_query.message.reply_text(info_text, reply_markup=keyboard)
        logger.info(f"[➕] Sent add channel request prompt to user {user_id}")
        
    except Exception as e:
        logger.error(f"[❌] Error handling add channel button for user {callback_query.from_user.id}: {e}")
        await send_error(callback_query.message, messages.ERROR_GENERIC)

async def handle_channel_selection(client: Client, message: types.Message) -> None:
    """Handle when a user selects a channel via the request chat button"""
    try:            
        user_id = message.from_user.id
        chat_id = message.chat_shared.chat.id

        logger.info(f"[✅] Received channel selection via chat_shared. Channel ID: {chat_id}, User ID: {user_id}")
        
        
        if not db.is_user_premium(user_id):
            await send_error(message, messages.ERROR_NOT_PREMIUM)
            return
            
        existing_channels = db.get_user_channels(user_id)
        for channel in existing_channels:
            if channel.get("channel_id") == chat_id:
                expiry_dt = channel.get("expiry_date")
                is_active = channel.get("is_active", False)
                days_left = "N/A"
                expiry_str = "N/A"
                if isinstance(expiry_dt, datetime):
                    days_left = max(0, (expiry_dt - datetime.now()).days)
                    expiry_str = expiry_dt.strftime('%d-%m-%Y')
                status = "✅ Active" if is_active else "❌ Inactive"
                channel_text = messages.channel_already_added_text(
                    channel_id=chat_id, status=status, expiry_str=expiry_str, days_left=days_left
                )
                await message.reply(channel_text, reply_markup=ReplyKeyboardRemove())
                logger.info(f"[ℹ️] User {user_id} tried to add already existing channel {chat_id}")
                return
        
        current_channels = len(existing_channels)
        max_channels = db.get_max_channels(user_id)
        
        if current_channels >= max_channels:
            limit_text = messages.channel_limit_reached_on_select_text(current_channels, max_channels)
            await message.reply(limit_text, reply_markup=ReplyKeyboardRemove())
            logger.info(f"[⚠️] User {user_id} tried to add channel {chat_id} but reached limit ({current_channels}/{max_channels})")
            return
        
        # Add channel to DB (expiry is tied to user's premium)
        if db.add_channel(chat_id, user_id): 
            success_text = messages.channel_added_success_text(
                channel_id=chat_id, current_channels=current_channels, max_channels=max_channels
            )
            await message.reply(success_text, reply_markup=ReplyKeyboardRemove())
            logger.info(f"[✅] Channel {chat_id} added for user {user_id} (slot {current_channels+1}/{max_channels})")
        else:
            await send_error(message, messages.ERROR_ADDING_CHANNEL)
            
    except Exception as e:
        user_id = message.from_user.id if message.from_user else "Unknown"
        logger.error(f"[❌] Error handling channel selection for user {user_id}: {e}")    
        await message.reply(messages.ERROR_PROCESSING_CHANNEL, reply_markup=ReplyKeyboardRemove())

async def handle_remove_channel_button(client: Client, callback_query: CallbackQuery) -> None:
    """Handle the Remove Channel button press (shows confirmation)"""
    try:
        await callback_query.answer()
        user_id = callback_query.from_user.id
        
        # Extract channel ID: remove_channel_{channel_id}
        _, _, channel_id_str = callback_query.data.partition("_channel_")
        try:
            channel_id = int(channel_id_str)
        except ValueError:
            logger.error(f"Invalid channel ID in remove callback: {callback_query.data}")
            await send_error(callback_query.message, messages.ERROR_GENERIC)
            return            

        confirm_text = messages.confirm_remove_channel_text(channel_id)
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(messages.BUTTON_CONFIRM_REMOVE, callback_data=f"confirm_remove_{channel_id}"),
                InlineKeyboardButton(messages.BUTTON_CANCEL, callback_data=f"channel_details_{channel_id}") # Go back to details
            ]
        ])
        await callback_query.message.edit_text(confirm_text, reply_markup=keyboard)
        logger.info(f"[🗑️] Requested confirmation to remove channel {channel_id} for user {user_id}")

    except Exception as e:
        logger.error(f"[❌] Error showing remove confirmation for user {callback_query.from_user.id}: {e}")
        await send_error(callback_query.message, messages.ERROR_GENERIC)

async def handle_confirm_remove_channel(client: Client, callback_query: CallbackQuery) -> None:
    """Handle the final confirmation to remove a channel"""
    try:
        await callback_query.answer()
        user_id = callback_query.from_user.id

        # Extract channel ID: confirm_remove_{channel_id}
        _, _, channel_id_str = callback_query.data.partition("_remove_")
        try:
            channel_id = int(channel_id_str)
        except ValueError:
            logger.error(f"Invalid channel ID in confirm remove callback: {callback_query.data}")
            await send_error(callback_query.message, messages.ERROR_GENERIC)
            return
            
        # Remove from DB
        if db.remove_channel(channel_id):
            success_text = messages.channel_removed_success_text(channel_id)
            # Go back to the main premium menu after removal
            await callback_query.message.edit_text(
                 success_text,
                 reply_markup=InlineKeyboardMarkup([
                     [InlineKeyboardButton(messages.BUTTON_BACK_TO_CHANNELS, callback_data="view_channels")]
                 ])
             )
            logger.info(f"[✅] Channel {channel_id} removed for user {user_id}")
        else:
            # Inform user about the failure (could be permission error or DB error)
            await callback_query.message.edit_text(
                 messages.ERROR_REMOVING_CHANNEL,
                 reply_markup=InlineKeyboardMarkup([
                     [InlineKeyboardButton(messages.BUTTON_BACK_TO_CHANNELS, callback_data="view_channels")]
                 ])
             )

    except Exception as e:
        logger.error(f"[❌] Error confirming channel removal for user {callback_query.from_user.id}: {e}")
        await send_error(callback_query.message, messages.ERROR_GENERIC) 