"""Handlers related to premium menus, plan display, and selection"""

from pyrogram import Client
from pyrogram.types import (
    CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
)
from datetime import datetime
import uuid 
from utils.logger import logger
from utils.db import db
from config.state import State
from .helpers import send_error, get_plan_name 
from .helpers import create_upgrade_plans_keyboard
from .helpers import get_premium_display_info
from config import messages
from config.config import Config 


async def handle_premium_menu_button(client: Client, callback_query: CallbackQuery) -> None:
    """Handles the main premium menu button or the /premium command"""
    try:
        user_id = callback_query.from_user.id
        
        status, text, markup = await get_premium_display_info(user_id)
        
        if status is None:
            # Error occurred
            await send_error(callback_query.message, text)
            return
            
        # Override text if not premium to use menu text
        if status is False:
            text = messages.PLANS_TEXT_MENU

        # Edit the original message or send new if needed
        if callback_query.message:
             await callback_query.message.edit_text(text, reply_markup=markup)
        else: # Should not happen from button, but maybe from command?
             await client.send_message(user_id, text, reply_markup=markup)
        await callback_query.answer()
            
    except Exception as e:
        logger.error(f"[❌] Error handling premium menu button: {e}")
        if callback_query.message:
             await send_error(callback_query.message, messages.ERROR_GENERIC)

async def handle_plan_selection(client: Client, callback_query: CallbackQuery) -> None:
    """Handle plan selection callback and show duration options"""
    try:
        await callback_query.answer()
        user_id = callback_query.from_user.id
        
        # Extract plan level: select_plan_{level}
        _, _, level_str = callback_query.data.partition("_plan_")
        try:
             channels = int(level_str)
        except ValueError:
             logger.error(f"Invalid level in plan selection callback: {callback_query.data}")
             await send_error(callback_query.message, messages.ERROR_PLAN_SELECTION)
             return
             
        # Determine plan name
        plan_name = get_plan_name(channels)
            
        # --- Get monthly price from Config.PLANS ---
        monthly_price = 0
        for _, _, plan_channels, price in Config.PLANS:
             if plan_channels == channels:
                  monthly_price = price
                  break
        
        if monthly_price <= 0:
             logger.error(f"Could not find valid price for plan with {channels} channels in Config.PLANS")
             await send_error(callback_query.message, messages.ERROR_PLAN_SELECTION)
             return
        # --- End price lookup ---
        
        # Show duration options
        duration_text = messages.duration_selection_text(
            plan_name=plan_name,
            channels=channels,
            monthly_price=monthly_price
        )
        
        # Create duration buttons (Prices in Stars)
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"1 Month - {monthly_price} ⭐", callback_data=f"buy_premium_{channels}_1")],
            [InlineKeyboardButton(f"3 Months - {monthly_price * 3} ⭐", callback_data=f"buy_premium_{channels}_3")],
            [InlineKeyboardButton(f"6 Months - {monthly_price * 6} ⭐", callback_data=f"buy_premium_{channels}_6")],
            [InlineKeyboardButton(f"12 Months - {monthly_price * 12} ⭐", callback_data=f"buy_premium_{channels}_12")],
            [InlineKeyboardButton(messages.BUTTON_BACK_TO_PLANS, callback_data="premium_menu")]
        ])
        
        await callback_query.message.edit_text(duration_text, reply_markup=keyboard)
        logger.info(f"[💲] Showed duration options for {plan_name} ({channels} channels) to user {user_id}")
        
    except Exception as e:
        logger.error(f"[❌] Error in plan selection for user {callback_query.from_user.id}: {e}")
        await send_error(callback_query.message, messages.ERROR_PLAN_SELECTION)

async def handle_upgrade_premium_button(client: Client, callback_query: CallbackQuery) -> None:
    """Handles the upgrade plan button"""
    try:
        user_id = callback_query.from_user.id

        premium_details = db.get_user_premium_details(user_id)
        if premium_details is None:
             await send_error(callback_query.message, messages.ERROR_PREMIUM_DATA)
             return
             
        is_premium, current_expiry_iso, current_max_channels = premium_details

        if not is_premium or not current_expiry_iso:
            await callback_query.answer("You are not currently a premium user.", show_alert=True)
            return
            
        # Get current plan name
        current_plan_name = get_plan_name(current_max_channels)

        # Check if already on max plan
        max_plan_channels = max(plan[2] for plan in Config.PLANS) if Config.PLANS else 0 # Added check for empty PLANS
        if current_max_channels >= max_plan_channels:
            await callback_query.answer(messages.ERROR_ALREADY_MAX_PLAN, show_alert=True)
            return
            
        # Format expiry date
        try:
             current_expiry_dt = datetime.fromisoformat(current_expiry_iso)
             current_expiry_str = current_expiry_dt.strftime("%d-%m-%Y")
        except ValueError:
             logger.error(f"[❌] Invalid expiry date format in DB for user {user_id} during upgrade: {current_expiry_iso}")
             await send_error(callback_query.message, messages.ERROR_PREMIUM_DATA)
             return
             
        text = messages.upgrade_options_text(current_plan_name, current_max_channels, current_expiry_str)
        markup = create_upgrade_plans_keyboard(current_max_channels)
        
        await callback_query.message.edit_text(text, reply_markup=markup)
        await callback_query.answer()

    except Exception as e:
        logger.error(f"[❌] Error handling upgrade premium button: {e}")
        await send_error(callback_query.message, messages.ERROR_UPGRADE)

async def handle_upgrade_plan_selection(client: Client, callback_query: CallbackQuery) -> None:
    """Handle the selection of a new plan during upgrade (Show confirmation)"""
    try:
        await callback_query.answer()
        user_id = callback_query.from_user.id
        
        # Extract target plan level: upgrade_plan_{level}
        _, _, level_str = callback_query.data.partition("_plan_")
        try:
             new_channels = int(level_str)
        except ValueError:
             logger.error(f"Invalid level in upgrade plan selection callback: {callback_query.data}")
             await send_error(callback_query.message, messages.ERROR_UPGRADE)
             return

        current_channels = db.get_max_channels(user_id)
        
        if new_channels <= current_channels:
            await send_error(callback_query.message, "You can only upgrade to a higher plan.") # Specific message
            return

        # Determine plan names 
        new_plan_name = get_plan_name(new_channels)
        
        # --- Get prices from Config.PLANS ---
        current_monthly_price = next((price for _, _, ch, price in Config.PLANS if ch == current_channels), 0)
        new_monthly_price = next((price for _, _, ch, price in Config.PLANS if ch == new_channels), 0)

        if current_monthly_price <= 0 or new_monthly_price <= 0:
             logger.error(f"Could not find valid prices for upgrade calculation ({current_channels} -> {new_channels})")
             await send_error(callback_query.message, messages.ERROR_UPGRADE)
             return
        # --- End price lookup ---

        # --- Upgrade Cost Calculation --- 
        # Get current subscription expiry
        current_expiry_iso = db.get_user_premium_details(user_id)[1]
        current_expiry_dt = datetime.fromisoformat(current_expiry_iso)
        remaining_days = (current_expiry_dt - datetime.now()).days
        
        if remaining_days <= 0:
            logger.error(f"Invalid remaining days for upgrade calculation: {remaining_days}")
            await send_error(callback_query.message, messages.ERROR_UPGRADE)
            return
            
        # Calculate daily prices for both plans
        current_daily_price = current_monthly_price / 31
        new_daily_price = new_monthly_price / 31
        
        # Calculate the price difference per day
        daily_price_difference = new_daily_price - current_daily_price
        
        # Calculate final upgrade cost based on remaining days and round to integer
        upgrade_cost_stars = round(daily_price_difference * remaining_days)
        upgrade_cost_display = upgrade_cost_stars  # Use the same rounded value for display
        
        if upgrade_cost_stars <= 0:
            logger.error(f"Calculated non-positive upgrade cost for user {user_id} from {current_channels} to {new_channels}")
            await send_error(callback_query.message, messages.ERROR_UPGRADE)
            return
        # ---------------------------------

        # Build confirmation text
        confirm_text = messages.upgrade_duration_text( 
            new_plan=new_plan_name,
            new_channels=new_channels,
            upgrade_cost=upgrade_cost_display # Pass the display cost (Stars)
        ) 
        
        # 1. Create the full payload with all necessary info
        upgrade_payload = f"upgrade_{user_id}_from_{current_channels}_to_{new_channels}_cost_{upgrade_cost_stars}_time_{int(datetime.now().timestamp())}"
        
        # 2. Generate a short unique ID
        unique_upgrade_id = str(uuid.uuid4())[:8] # Use first 8 chars of UUID for brevity
        
        # 3. Store the full payload in State, keyed by the unique ID
        if not hasattr(State, 'pending_upgrades'):
             State.pending_upgrades = {} # Initialize if it doesn't exist
        State.pending_upgrades[unique_upgrade_id] = upgrade_payload
        logger.info(f"[🔒] Stored pending upgrade payload for user {user_id} with ID: {unique_upgrade_id}")
        
        # 4. Use only the unique ID in the callback data
        keyboard = InlineKeyboardMarkup([
            # Callback leads to handle_confirm_upgrade in invoice_handlers.py
            [InlineKeyboardButton(messages.BUTTON_CONFIRM_UPGRADE, callback_data=f"confirm_upgrade_{unique_upgrade_id}")],
            [InlineKeyboardButton(messages.BUTTON_BACK_TO_MENU, callback_data="premium_menu")] 
        ])
        
        await callback_query.message.edit_text(confirm_text, reply_markup=keyboard)
        logger.info(f"[⬆️] Showed upgrade confirmation ({current_channels} -> {new_channels}) to user {user_id}, Cost: {upgrade_cost_stars} ⭐, Pending ID: {unique_upgrade_id}")

    except Exception as e:
        logger.error(f"[❌] Error in upgrade plan selection for user {callback_query.from_user.id}: {e}")
        await send_error(callback_query.message, messages.ERROR_UPGRADE) 