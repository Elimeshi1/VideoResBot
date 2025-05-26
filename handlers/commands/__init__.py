"""Command handlers package"""

from pyrogram import Client, filters
from pyrogram.handlers import MessageHandler
from utils.logger import logger

from .general import (
    start_command_handler,
    help_command_handler,
    cancel_command_handler,
    handle_private_other_messages,
    refund_command_handler
)
from .premium import (
    handle_premium_purchase_command,
)

__all__ = [
    # General Commands
    "start_command_handler",
    "help_command_handler",
    "cancel_command_handler",
    "refund_command_handler",
    # Premium Commands
    "handle_premium_purchase_command",
    # Catch-all
    "handle_private_other_messages",
]

def register_command_handlers(app: Client):
    # --- Command Handlers (Group 1) ---
    handlers_to_register = [
        (start_command_handler, ["start"]), 
        (help_command_handler, ["help"]), 
        (cancel_command_handler, ["cancel"]), 
        (handle_premium_purchase_command, ["premium"]),
        (refund_command_handler, ["refund"]),
    ]
    
    for handler, commands in handlers_to_register:
        app.add_handler(MessageHandler(handler, filters.command(commands) & filters.private), group=1)
        
    app.add_handler(MessageHandler(
        handle_private_other_messages,
        filters.private &
        ~filters.video & # Exclude videos (handled in video package)
        ~filters.command(["start", "help", "cancel", "premium", "refund"]) &
        ~filters.service &
        ~filters.chat_shared # Exclude chat shared (handled in payment package)
    ), group=4)
