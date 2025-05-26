"""Helper functions for payment-related handlers"""

from config.config import Config
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton 
from datetime import datetime
from utils.db import db
from utils.logger import logger
from config import messages


async def send_error(message, error_text: str) -> None:
    """Send error message to user"""
    try:
        error_message = f"❌ **ERROR** ❌\n\n{error_text}"
        
        # Only use edit_text for messages from callback queries (not direct command messages)
        # This is more reliable than checking for hasattr(message, 'edit_text')
        from pyrogram.types import Message as PyrogramMessage
        is_callback_message = not isinstance(message, PyrogramMessage)
        
        if is_callback_message:
            await message.edit_text(error_message)
        else:
            await message.reply_text(error_message)
            
    except Exception as e:
        logger.error(f"Error sending error message: {e}")

def get_plan_name(channels: int) -> str:
    """Returns the plan name based on the number of channels."""
    if channels >= 5:
        return "Premium Pro"
    elif channels >= 3:
        return "Premium+"
    elif channels >= 1:
        return "Premium Basic"
    else:
        return "Unknown Plan" # Should not happen for valid premium users

# --- Keyboard Creation Helper Functions --- ADDED from menu_handlers

def create_premium_management_keyboard(user_id: int, num_channels: int, max_channels: int) -> InlineKeyboardMarkup:
    """Creates the keyboard with management options for premium users."""
    buttons = [
        [
            InlineKeyboardButton(messages.BUTTON_ADD_CHANNEL, callback_data="add_channel_btn"),
            InlineKeyboardButton(messages.BUTTON_MY_CHANNELS, callback_data="view_channels")
        ]
    ]
    # Add upgrade button only if not on max plan
    max_plan_channels = max(plan[2] for plan in Config.PLANS) if Config.PLANS else 0
    if max_channels < max_plan_channels:
        buttons.append([InlineKeyboardButton(messages.BUTTON_UPGRADE_PLAN, callback_data="upgrade_premium")])
        
    return InlineKeyboardMarkup(buttons)

def create_plans_keyboard() -> InlineKeyboardMarkup:
    """Creates the keyboard showing the available premium plans."""
    buttons = []
    
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
        
    is_premium, expiry_iso, max_channels = premium_details
    
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
            plan_name = get_plan_name(max_channels)
            
            text = messages.premium_status_text(
                expiry_date_str, plan_name, num_channels, 
                max_channels, active_channels, days_remaining
            )
            # Create keyboard
            markup = create_premium_management_keyboard(user_id, num_channels, max_channels)
            return True, text, markup
            
        except Exception as detail_err:
            logger.error(f"[❌] Error calculating premium details for user {user_id}: {detail_err}")
            return None, messages.ERROR_CALCULATING_DAYS, None
            
    else:
        # Not premium: Show plans
        text = messages.PLANS_TEXT_MENU  # Caller can override this if needed
        markup = create_plans_keyboard()
        return False, text, markup
