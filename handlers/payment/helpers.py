"""Helper functions for payment-related handlers"""

from config.config import Config
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton 
from datetime import datetime
from utils.db import db
from utils.logger import logger
from config import messages
from utils.decorators import get_plan_name, send_error_message

# Use centralized send_error_message function from decorators module

# --- Keyboard Creation Helper Functions --- ADDED from menu_handlers

def create_premium_management_keyboard(user_id: int, num_channels: int, max_channels: int, is_trial: bool = False) -> InlineKeyboardMarkup:
    """Creates the keyboard with management options for premium users."""
    buttons = [
        [
            InlineKeyboardButton(messages.BUTTON_ADD_CHANNEL, callback_data="add_channel_btn"),
            InlineKeyboardButton(messages.BUTTON_MY_CHANNELS, callback_data="view_channels")
        ]
    ]
    # Add upgrade button only if not on max plan and not a trial user
    max_plan_channels = max(plan[2] for plan in Config.PLANS) if Config.PLANS else 0
    if max_channels < max_plan_channels and not is_trial:
        buttons.append([InlineKeyboardButton(messages.BUTTON_UPGRADE_PLAN, callback_data="upgrade_premium")])
        
    return InlineKeyboardMarkup(buttons)

def create_plans_keyboard(user_id: int = None) -> InlineKeyboardMarkup:
    """Creates the keyboard showing the available premium plans."""
    buttons = []
    
    # Add trial button if user hasn't used it yet
    if user_id:
        if not db.has_used_trial(user_id):
            buttons.append([InlineKeyboardButton(messages.BUTTON_START_TRIAL, callback_data="start_trial")])
    
    for plan_id, name, channels, price in Config.PLANS:
        # Price is monthly base
        button_text = f"{name} ({channels} {'channel' if channels == 1 else 'channels'}) - {price} ⭐/mo"
        buttons.append([InlineKeyboardButton(button_text, callback_data=f"select_plan_{channels}")]) # Use channels in callback

    return InlineKeyboardMarkup(buttons)

def create_upgrade_plans_keyboard(current_max_channels: int) -> InlineKeyboardMarkup:
     """Creates the keyboard for selecting a plan to upgrade to."""
     buttons = []
     for plan_id, name, channels, price in Config.PLANS:
         if channels > current_max_channels:
             button_text = f"Upgrade to {name} ({channels} channels)"
             buttons.append([InlineKeyboardButton(button_text, callback_data=f"upgrade_plan_{channels}")])
     buttons.append([InlineKeyboardButton(messages.BUTTON_BACK_TO_MENU, callback_data="premium_menu")])
     return InlineKeyboardMarkup(buttons)

async def get_premium_display_info(user_id):
    """Common helper function to get premium display information for a user"""
    premium_details = db.get_user_premium_details(user_id)
    if premium_details is None:
        return None, messages.ERROR_PREMIUM_DATA, None
        
    is_premium, expiry_iso, max_channels, is_trial = premium_details
    
    if is_premium and expiry_iso:
        # Premium user: Show status and management options
        try:
            expiry_dt = datetime.fromisoformat(expiry_iso)
            now = datetime.now()
            days_remaining = (expiry_dt - now).days if expiry_dt > now else 0
            expiry_date_str = expiry_dt.strftime("%d-%m-%Y")
            
            # Get current channel count and plan name
            user_channels = db.get_user_channels(user_id)
            num_channels = len(user_channels)
            active_channels = sum(1 for ch in user_channels if ch['is_active'])
            
            # Set plan name based on trial status
            if is_trial:
                plan_name = "7-Day Free Trial"
            else:
                plan_name = get_plan_name(max_channels)
            
            text = messages.premium_status_text(
                expiry_date_str, plan_name, num_channels, 
                max_channels, active_channels, days_remaining, is_trial
            )
            # Create keyboard
            markup = create_premium_management_keyboard(user_id, num_channels, max_channels, is_trial)
            return True, text, markup
            
        except Exception as detail_err:
            logger.error(f"[❌] Error calculating premium details for user {user_id}: {detail_err}")
            return None, messages.ERROR_CALCULATING_DAYS, None
            
    else:
        # Not premium: Show plans
        text = messages.PLANS_TEXT_MENU  # Caller can override this if needed
        markup = create_plans_keyboard(user_id)
        return False, text, markup
