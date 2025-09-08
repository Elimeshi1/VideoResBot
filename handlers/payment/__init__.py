"""Initializes the payment handlers package and provides registration function."""

from pyrogram import Client, filters
from pyrogram.handlers import (
    CallbackQueryHandler, MessageHandler, PreCheckoutQueryHandler
)
from utils.logger import logger

from .menu_handlers import (
    handle_premium_menu_button,
    handle_plan_selection,
    handle_upgrade_premium_button,
    handle_upgrade_plan_selection,
    handle_start_trial
)
from .invoice_handlers import (
    handle_premium_purchase_button as handle_invoice_purchase_button, # Alias for callback
    handle_confirm_upgrade,
    handle_pre_checkout_query_handler,
    handle_successful_payment
)
from .channel_management_handlers import (
    handle_add_channel_button,
    handle_channel_selection,
    handle_remove_channel_button,
    handle_confirm_remove_channel
)
from .channel_view_handlers import (
    handle_view_channels_button,
    handle_channel_details
)

# Collect all handlers exported by this package for easier iteration
# This relies on the __all__ defined below
_payment_handlers_map = {
    'handle_premium_menu_button': handle_premium_menu_button,
    'handle_plan_selection': handle_plan_selection,
    'handle_upgrade_premium_button': handle_upgrade_premium_button,
    'handle_upgrade_plan_selection': handle_upgrade_plan_selection,
    'handle_start_trial': handle_start_trial,
    'handle_invoice_purchase_button': handle_invoice_purchase_button,
    'handle_confirm_upgrade': handle_confirm_upgrade,
    'handle_pre_checkout_query_handler': handle_pre_checkout_query_handler,
    'handle_successful_payment': handle_successful_payment,
    'handle_add_channel_button': handle_add_channel_button,
    'handle_channel_selection': handle_channel_selection,
    'handle_remove_channel_button': handle_remove_channel_button,
    'handle_confirm_remove_channel': handle_confirm_remove_channel,
    'handle_view_channels_button': handle_view_channels_button,
    'handle_channel_details': handle_channel_details,
}

__all__ = list(_payment_handlers_map.keys())

def register_payment_handlers(app: Client):
    """Registers all payment-related callback query handlers."""
    
    callbacks_to_register = []
    
    # Register lifecycle handlers first (Group 1)
    if 'handle_pre_checkout_query_handler' in _payment_handlers_map:
        handler_func = _payment_handlers_map['handle_pre_checkout_query_handler']
        app.add_handler(PreCheckoutQueryHandler(handler_func), group=1)
        
    if 'handle_successful_payment' in _payment_handlers_map:
        handler_func = _payment_handlers_map['handle_successful_payment']
        app.add_handler(MessageHandler(handler_func, filters.successful_payment), group=1)
        
    if 'handle_channel_selection' in _payment_handlers_map:
        handler_func = _payment_handlers_map['handle_channel_selection']
        app.add_handler(MessageHandler(handler_func, filters.chat_shared & filters.private), group=1)

    # Prepare callback handlers (Group 2)
    for handler_name, handler_func in _payment_handlers_map.items():
        # Skip the ones already registered
        if handler_name in ['handle_pre_checkout_query_handler', 'handle_successful_payment', 'handle_channel_selection']:
            continue
            
        # Determine regex pattern based on handler name convention
        callback_pattern = None
        if handler_name == "handle_plan_selection":
            callback_pattern = r"select_plan_\d+"
        elif handler_name == "handle_upgrade_plan_selection":
            callback_pattern = r"upgrade_plan_\d+"
        elif handler_name == "handle_premium_menu_button":
            callback_pattern = r"premium_menu"
        elif handler_name == "handle_upgrade_premium_button":
            callback_pattern = r"upgrade_premium"
        elif handler_name == "handle_start_trial":
            callback_pattern = r"start_trial"
        elif handler_name == "handle_invoice_purchase_button": # Using aliased name
            callback_pattern = r"buy_premium_(\d+)_(\d+)"
        elif handler_name == "handle_confirm_upgrade":
             # Ensure this matches the callback data generated in menu_handlers (8 hex chars)
             # Corrected regex to be more specific
            callback_pattern = r"confirm_upgrade_([a-f0-9]{8})"
        elif handler_name == "handle_add_channel_button":
            callback_pattern = r"add_channel_btn"
        elif handler_name == "handle_remove_channel_button":
             # This button shows details for a specific channel before confirmation
             # Callback name should match button creation in channel_view_handlers
             callback_pattern = r"remove_channel_(-?\d+)" 
        elif handler_name == "handle_confirm_remove_channel":
            callback_pattern = r"confirm_remove_(-?\d+)"
        elif handler_name == "handle_view_channels_button":
            callback_pattern = r"view_channels"
        elif handler_name == "handle_channel_details":
            callback_pattern = r"channel_details_(-?\d+)"
        # Add other callback patterns here if needed
            
        if callback_pattern:
            callbacks_to_register.append((handler_func, callback_pattern))
        else:
            logger.warning(f"    - Could not determine regex pattern for payment handler: {handler_name}. Skipping.")

    # Register callback handlers (Group 2)
    for handler_func, pattern in callbacks_to_register:
        app.add_handler(CallbackQueryHandler(handler_func, filters.regex(f"^{pattern}$")), group=2)
