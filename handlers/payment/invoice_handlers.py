"""Handlers related to sending invoices and processing payment callbacks"""

from pyrogram import Client, types
from pyrogram.types import (
    PreCheckoutQuery, CallbackQuery
)
from datetime import datetime, timedelta

from utils.logger import logger
from utils.db import db
from utils.decorators import send_error_message, get_plan_name 
from config import messages
from config.config import Config
from config.state import State 

async def handle_premium_purchase_button(client: Client, callback_query: CallbackQuery) -> None:
    """Handle the buy premium button callback (Sends Purchase Invoice)"""
    try:
        await callback_query.answer()
        user_id = callback_query.from_user.id
        
        # Extract channels and months from callback_data: buy_premium_{channels}_{months}
        parts = callback_query.data.split('_')
        channels = int(parts[2])
        months = int(parts[3])
        
        # Determine plan name (Use helper)
        plan_name = get_plan_name(channels)
            
        # --- Get monthly price from Config.PLANS ---
        monthly_price = 0
        for _, _, plan_channels, price in Config.PLANS:
             if plan_channels == channels:
                  monthly_price = price
                  break
        
        if monthly_price <= 0:
             logger.error(f"Could not find valid price for purchase plan with {channels} channels in Config.PLANS")
             await send_error_message(callback_query.message, messages.ERROR_PURCHASE)
             return

        # Calculate total price in Stars
        total_price_stars = monthly_price * months 

        # Generate invoice payload
        # Example: user_123_plan_3_months_12_time_1678886400
        payload = f"user_{user_id}_plan_{channels}_months_{months}_time_{int(datetime.now().timestamp())}"
        
        # Define LabeledPrice (amount should be in the smallest unit of the currency - Stars)
        prices = [types.LabeledPrice(label=f"{plan_name} ({months} Mo)", amount=total_price_stars)] 

        logger.info(f"[💲] Sending purchase invoice for {plan_name} ({months} months) to user {user_id}, price: {total_price_stars} ⭐, payload: {payload}")

        await client.send_invoice(
            chat_id=user_id,
            title=messages.invoice_title(plan_name, months),
            description=messages.invoice_description(channels, months),
            payload=payload,
            currency="XTR", # Using Telegram Stars currency code
            prices=prices,
        )
        
    except Exception as e:
        logger.error(f"[❌] Error sending purchase invoice: {e}")
        await send_error_message(callback_query.message, messages.ERROR_PURCHASE)


async def handle_confirm_upgrade(client: Client, callback_query: CallbackQuery) -> None:
    """Handle the final confirmation to upgrade (Sends Upgrade Invoice)"""
    try:
        await callback_query.answer()
        user_id = callback_query.from_user.id
        parts = callback_query.data.split('_')
        if len(parts) != 3:
             logger.error(f"Invalid confirm_upgrade callback data format: {callback_query.data}")
             await send_error_message(callback_query.message, messages.ERROR_UPGRADE)
             return
             
        unique_upgrade_id = parts[2]
        
        # Retrieve the full payload from State
        if not hasattr(State, 'pending_upgrades') or unique_upgrade_id not in State.pending_upgrades:
             logger.error(f"Pending upgrade ID {unique_upgrade_id} not found in State for user {user_id}.")
             await send_error_message(callback_query.message, "Upgrade session expired or invalid. Please try again.") # Specific error
             return
             
        payload = State.pending_upgrades.pop(unique_upgrade_id) # Retrieve and remove
        logger.info(f"[🔓] Retrieved pending upgrade payload for ID {unique_upgrade_id}: {payload}")
        
        payload_parts = payload.split('_')
        if len(payload_parts) < 7 or not payload.startswith("upgrade_") or payload_parts[1] != str(user_id):
             logger.error(f"Invalid payload retrieved from State: {payload}") 
             await send_error_message(callback_query.message, messages.ERROR_UPGRADE)
             return
             
        new_channels = int(payload_parts[5])
        upgrade_cost_stars = int(payload_parts[7]) 

        # Determine plan name (Use helper)
        new_plan_name = get_plan_name(new_channels)
        
        # Validate cost again
        if upgrade_cost_stars <= 0:
            logger.error(f"[❌] Invalid upgrade cost detected in retrieved payload: {upgrade_cost_stars}")
            await send_error_message(callback_query.message, messages.ERROR_UPGRADE)
            return
             
        # Define LabeledPrice for the upgrade cost
        prices = [types.LabeledPrice(label=f"Upgrade to {new_plan_name}", amount=upgrade_cost_stars)]

        logger.info(f"[⬆️] Sending upgrade invoice for {new_plan_name} to user {user_id}, cost: {upgrade_cost_stars} ⭐, payload: {payload}")

        # Send invoice for the upgrade cost
        await client.send_invoice(
            chat_id=user_id,
            title=f"Upgrade to {new_plan_name}",
            description=f"Upgrade cost to move to the {new_plan_name} plan.",
            payload=payload, # Use the specific upgrade payload retrieved from State
            currency="XTR", # Telegram Stars
            prices=prices,
        )
        
    except Exception as e:
        logger.error(f"[❌] Error sending upgrade invoice: {e}")
        await send_error_message(callback_query.message, messages.ERROR_UPGRADE)

async def handle_pre_checkout_query_handler(client: Client, query: PreCheckoutQuery) -> None:
    """Handles pre-checkout queries to validate the purchase/upgrade"""
    try:
        user_id = query.from_user.id
        payload = query.invoice_payload
        logger.info(f"[❔] PreCheckoutQuery received from {user_id}, payload: {payload}")

        # --- Payload Validation ---
        if payload.startswith("user_"): # Regular purchase
            parts = payload.split('_')
            # user_{user_id}_plan_{channels}_months_{months}_time_{ts}
            if len(parts) < 7 or parts[1] != str(user_id):
                logger.warning(f"[⚠️] Invalid purchase payload structure or mismatched user ID: {payload}")
                await query.answer(ok=False, error_message="Invalid purchase details.")
                return

        elif payload.startswith("upgrade_"): # Upgrade purchase
            parts = payload.split('_')
            # upgrade_{user_id}_from_{current_channels}_to_{new_channels}_cost_{upgrade_cost_stars}
            if len(parts) < 7 or parts[1] != str(user_id):
                logger.warning(f"[⚠️] Invalid upgrade payload structure or mismatched user ID: {payload}")
                await query.answer(ok=False, error_message="Invalid upgrade details.")
                return
            
            # Check if user is still eligible for this upgrade (haven't changed plan since)
            current_channels_db = db.get_max_channels(user_id)
            from_channels_payload = int(parts[3])
            if current_channels_db != from_channels_payload:
                logger.warning(f"[⚠️] User's plan changed since upgrade initiated. DB: {current_channels_db}, Payload: {from_channels_payload}")
                await query.answer(ok=False, error_message="Your plan has changed. Please restart the upgrade process.")
                return
                 
        else:
            logger.error(f"[❌] Unknown payload type received in PreCheckoutQuery: {payload}")
            await query.answer(ok=False, error_message="Unknown transaction type.")
            return

        # If all checks pass:
        logger.info(f"[✅] PreCheckoutQuery approved for user {user_id}, payload: {payload}")
        await query.answer(ok=True)

    except Exception as e:
        logger.error(f"[❌] Error processing PreCheckoutQuery for user {query.from_user.id}: {e}")
        await query.answer(ok=False, error_message=messages.ERROR_PURCHASE) 


async def handle_successful_payment(client: Client, message: types.Message) -> None:
    """Handles successful payment messages"""
    try:
        user_id = message.from_user.id
        if not message.successful_payment:
             logger.warning(f"Received message without successful_payment object from user {user_id}")
             return
             
        payment_info = message.successful_payment
        payload = payment_info.invoice_payload
        telegram_charge_id = payment_info.telegram_payment_charge_id
        total_amount = payment_info.total_amount
        currency = payment_info.currency
        
        logger.info(f"[✅] SuccessfulPayment received from user {user_id}, payload: {payload}, currency: {currency}, amount: {total_amount}, telegram_charge_id: {telegram_charge_id}")

        # Process based on payload type
        if payload.startswith("user_"): # Regular purchase
            # Extract details: user_{user_id}_plan_{channels}_months_{months}_time_{ts}
            parts = payload.split('_')
            if len(parts) < 7:
                 logger.error(f"[❌] Invalid user payload structure in SuccessfulPayment: {payload}")
                 await send_error_message(message, messages.ERROR_GENERIC)
                 return
                 
            channels = int(parts[3])
            months = int(parts[5])
            
            # Calculate expiry date
            expiry_date = datetime.now() + timedelta(days=31 * months) # Approximate

            success = db.set_user_premium(user_id=user_id, max_channels=channels, months=months)
            
            if success:
                expiry_date_str = expiry_date.strftime("%d-%m-%Y") # Get expiry from calculation above
                await message.reply_text(messages.successful_payment_text(expiry_date_str))
                logger.info(f"[✅] User {user_id} premium activated/updated via set_user_premium. Expires: {expiry_date_str}, Channels: {channels}")
            else:
                logger.error(f"[❌] Failed to update database using set_user_premium for user {user_id}! Payload: {payload}")
                await send_error_message(message, messages.ERROR_GENERIC) 

        elif payload.startswith("upgrade_"): # Upgrade purchase
            # Extract details: upgrade_{user_id}_from_{c_from}_to_{c_to}_cost_{cost_stars}
            parts = payload.split('_')
            if len(parts) < 7:
                 logger.error(f"[❌] Invalid upgrade payload structure in SuccessfulPayment: {payload}")
                 await send_error_message(message, messages.ERROR_GENERIC)
                 return
                 
            new_channels = int(parts[5])
            
            success = db.upgrade_user_channels(user_id, new_channels)

            if success:
                # Determine plan name (Use helper)
                new_plan_name = get_plan_name(new_channels)
                await message.reply_text(messages.upgrade_successful_text(new_plan_name, new_channels))
                logger.info(f"[✅] User {user_id} successfully upgraded to {new_channels} channels. Charge ID: {telegram_charge_id}")
            else:
                logger.error(f"[❌] Failed to update database for user {user_id} after successful upgrade payment! Charge ID: {telegram_charge_id}")
                await send_error_message(message, messages.ERROR_GENERIC)
                
        else:
            logger.error(f"[❌] Unknown payload type received in SuccessfulPayment from user {user_id}: {payload}")
            await send_error_message(message, messages.ERROR_GENERIC)

    except Exception as e:
        logger.error(f"[❌] Error processing SuccessfulPayment for user {message.from_user.id}: {e}")
        # Avoid sending another error if the original message was the error source
        if hasattr(message, 'chat') and hasattr(message.chat, 'id'):
             await send_error_message(message, messages.ERROR_GENERIC) 