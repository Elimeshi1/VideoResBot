"""Handlers related to viewing channel lists and details"""

from pyrogram import Client
from pyrogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
)
from datetime import datetime

from utils.logger import logger
from utils.db import db
from .helpers import send_error
from config import messages

async def handle_view_channels_button(client: Client, callback_query: CallbackQuery) -> None:
    """Handle the View Channels button press (Shows list of channels)"""
    try:
        await callback_query.answer()
        user_id = callback_query.from_user.id
        
        if not db.is_user_premium(user_id):
            await send_error(callback_query.message, messages.ERROR_NOT_PREMIUM)
            return
            
        channels_data = db.get_user_channels(user_id)
        
        if not channels_data:
            no_channels_text = messages.NO_CHANNELS_TEXT 
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(messages.BUTTON_ADD_CHANNEL, callback_data="add_channel_btn")],
                [InlineKeyboardButton(messages.BUTTON_BACK_TO_MENU, callback_data="premium_menu")]
            ])
            await callback_query.message.edit_text(no_channels_text, reply_markup=keyboard)
            logger.info(f"[ℹ️] User {user_id} viewed channels - none found.")
            return
            
        total_channels = len(channels_data)
        active_channels = sum(1 for c in channels_data if c.get("is_active"))
        channels_text = messages.view_channels_text(active_channels, total_channels)
        
        buttons = []

        for channel in channels_data:
            channel_id = channel.get("channel_id")
            is_active = channel.get("is_active", False)
            if channel_id is None: continue
            status_emoji = "✅" if is_active else "❌"
            callback_data = f"channel_details_{channel_id}"
            buttons.append([InlineKeyboardButton(f"{status_emoji} Channel {channel_id}", callback_data=callback_data)])
        
        max_channels = db.get_max_channels(user_id)
        if total_channels < max_channels:
             buttons.append([InlineKeyboardButton(messages.BUTTON_ADD_CHANNEL, callback_data="add_channel_btn")])
        buttons.append([InlineKeyboardButton(messages.BUTTON_BACK_TO_MENU, callback_data="premium_menu")]) 
        
        keyboard = InlineKeyboardMarkup(buttons)
        await callback_query.message.edit_text(channels_text, reply_markup=keyboard)
        logger.info(f"[📋] Listed channels ({active_channels}/{total_channels}) for user {user_id}")
        
    except Exception as e:
        logger.error(f"[❌] Error in view channels for user {callback_query.from_user.id}: {e}")
        await send_error(callback_query.message, messages.ERROR_VIEWING_CHANNELS)

async def handle_channel_details(client: Client, callback_query: CallbackQuery) -> None:
    """Handle when a user selects a specific channel from the list (Shows details)"""
    try:
        await callback_query.answer()
        user_id = callback_query.from_user.id
        
        # Extract channel ID: channel_details_{channel_id}
        _, _, channel_id_str = callback_query.data.partition("_details_")
        try:
            channel_id = int(channel_id_str)
        except ValueError:
            logger.error(f"Invalid channel ID in details callback: {callback_query.data}")
            await send_error(callback_query.message, messages.ERROR_GENERIC)
            return

        channel_data = db.get_channel_details(user_id, channel_id) 

        if not channel_data:
            logger.warning(f"Channel {channel_id} not found for user {user_id} in details view.")
            await callback_query.message.edit_text(
                f"Channel `{channel_id}` not found or does not belong to you.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(messages.BUTTON_BACK_TO_CHANNELS, callback_data="view_channels")]
                ])
            )
            return

        # Extract details safely
        expiry_dt = channel_data.get("expiry_date")
        is_active = channel_data.get("is_active", False)
        days_left = "N/A"
        expiry_str = "N/A"
        if isinstance(expiry_dt, datetime):
            days_left = max(0, (expiry_dt - datetime.now()).days)
            expiry_str = expiry_dt.strftime('%d-%m-%Y')
        status = "✅ Active" if is_active else "❌ Inactive"

        details_text = messages.channel_details_text(
            channel_id=channel_id, status=status, expiry_str=expiry_str, days_left=days_left
        )
        keyboard = InlineKeyboardMarkup([
            # Callback leads to handle_remove_channel_button in channel_management_handlers.py
            [InlineKeyboardButton(messages.BUTTON_REMOVE_CHANNEL, callback_data=f"remove_channel_{channel_id}")],
            [InlineKeyboardButton(messages.BUTTON_BACK_TO_CHANNELS, callback_data="view_channels")] 
        ])
        await callback_query.message.edit_text(details_text, reply_markup=keyboard)
        logger.info(f"[ℹ️] Showed details for channel {channel_id} to user {user_id}")

    except Exception as e:
        logger.error(f"[❌] Error showing channel details for user {callback_query.from_user.id}: {e}")
        await send_error(callback_query.message, messages.ERROR_GENERIC) 