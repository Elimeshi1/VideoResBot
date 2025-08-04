from pyrogram import Client
from pyrogram.types import Message, ReplyKeyboardRemove
from utils.logger import logger
from utils.cleanup import delete_scheduled_message, clean_up_tracking_info
from config.state import State
from config import messages
from utils.db import db
from config.config import Config
from utils.queue_manager import get_active_videos_count

async def start_command_handler(client: Client, message: Message) -> None:
    """Handle the /start command"""
    try:
        user_id = message.from_user.id
        user_name = message.from_user.first_name
        
        # Check if user is banned
        is_banned, ban_reason = db.is_user_banned(user_id)
        if is_banned:
            logger.warning(f"[🚫] Banned user {user_id} ({user_name}) attempted to use /start command")
            await message.reply_text(messages.USER_BANNED(ban_reason), reply_markup=ReplyKeyboardRemove())
            return
        
        logger.info(f"[👋] New /start command from user {user_id} ({user_name})")
        
        db.add_user(user_id, False)
        
        # Remove any existing ReplyKeyboardMarkup
        await message.reply_text(messages.START_TEXT, reply_markup=ReplyKeyboardRemove())
        
    except Exception as e:
        logger.error(f"[❌] Error handling start command: {e}")
        await message.reply_text(messages.ERROR_GENERIC, reply_markup=ReplyKeyboardRemove())

async def help_command_handler(client: Client, message: Message) -> None:
    """Handles the /help command"""
    try:
        user_id = message.from_user.id
        user_name = message.from_user.first_name
        
        # Check if user is banned
        is_banned, ban_reason = db.is_user_banned(user_id)
        if is_banned:
            logger.warning(f"[🚫] Banned user {user_id} ({user_name}) attempted to use /help command")
            await message.reply_text(messages.USER_BANNED(ban_reason), reply_markup=ReplyKeyboardRemove())
            return
        
        logger.info(f"[ℹ️] Received help command from user {user_id} ({user_name})")
        
        db.add_user(user_id, False)    

        # Remove any existing ReplyKeyboardMarkup
        await message.reply_text(messages.HELP_TEXT, reply_markup=ReplyKeyboardRemove())

    except Exception as e:
        logger.error(f"Error handling help command: {e}")
        await message.reply_text(messages.ERROR_GENERIC, reply_markup=ReplyKeyboardRemove())

async def cancel_command_handler(client: Client, message: Message) -> None:
    """Handles the /cancel command to cancel video processing"""
    try:
        user_id = message.from_user.id
        user_name = message.from_user.first_name

        # Check if user is banned
        is_banned, ban_reason = db.is_user_banned(user_id)
        if is_banned:
            logger.warning(f"[🚫] Banned user {user_id} ({user_name}) attempted to use /cancel command")
            await message.reply_text(messages.USER_BANNED(ban_reason), reply_markup=ReplyKeyboardRemove())
            return

        db.add_user(user_id, False)
        
        # Check if user has any active videos
        active_count = get_active_videos_count(user_id, is_channel=False)
        
        if active_count == 0 and user_id not in State.active_users:
            logger.info(f"[❌] User {user_id} ({user_name}) tried to cancel but has no active videos")
            # Use message constant and remove keyboard
            await message.reply_text(messages.CANCEL_NO_ACTIVE_VIDEO, reply_markup=ReplyKeyboardRemove())
            return
        
        transfer_msg_id = None
        for t_id, u_info in list(State.user_videos.items()):
            if isinstance(u_info, int) and u_info == user_id:
                if t_id in State.video_info:
                    transfer_msg_id = t_id
                    break
                else:
                    logger.warning(f"[⚠️] Found stale user_videos entry for user {user_id}, transfer ID {t_id} not in video_info during cancel.")
            
        if not transfer_msg_id:
            logger.warning(f"[⚠️] Could not find active video processing for user {user_id} ({user_name}) during cancel.")
            # Only remove from active_users if there are no active videos
            if active_count == 0:
                State.active_users.discard(user_id)
            # Use message constant and remove keyboard
            await message.reply_text(messages.CANCEL_NO_ACTIVE_VIDEO, reply_markup=ReplyKeyboardRemove())
            return
        
        _, scheduled_msg_id, _, _, _ = State.video_info[transfer_msg_id]
        
        await delete_scheduled_message(scheduled_msg_id)
        clean_up_tracking_info(transfer_msg_id, user_id)
        
        # Check if user still has active videos AFTER cleanup
        remaining_count = get_active_videos_count(user_id, is_channel=False)
        
        if remaining_count > 0:
            # Keep user in active_users as they still have videos
            await message.reply_text(
                messages.CANCEL_STILL_ACTIVE(remaining_count),
                reply_markup=ReplyKeyboardRemove()
            )
        else:
            # Remove user from active_users
            State.active_users.discard(user_id)
            # Use default message as this was the last video and remove keyboard
            await message.reply_text(messages.CANCEL_SUCCESS, reply_markup=ReplyKeyboardRemove())
            
        logger.info(f"[✅] Successfully canceled video processing for user {user_id} ({user_name}). Remaining videos: {remaining_count}")
        
    except Exception as e:
        logger.error(f"Error handling cancel command: {e}", exc_info=True)
        await message.reply_text(messages.ERROR_CANCEL, reply_markup=ReplyKeyboardRemove())

async def handle_private_other_messages(client: Client, message: Message) -> None:
    """Handles non-video messages in private chats (catch-all)"""
    try:
        # Skip sending response for refunded payment messages
        if hasattr(message, 'refunded_payment'):
            return
        
        user_id = message.from_user.id
        
        # Check if user is banned
        is_banned, ban_reason = db.is_user_banned(user_id)
        if is_banned:
            logger.warning(f"[🚫] Banned user {user_id} attempted to send message")
            await message.reply_text(messages.USER_BANNED(ban_reason), reply_markup=ReplyKeyboardRemove())
            return
            
        db.add_user(user_id, False)
        await message.reply_text(messages.OTHER_MESSAGE_PROMPT, reply_markup=ReplyKeyboardRemove())
        logger.info(f"[ℹ️] Sent response to user {user_id} for non-video message")
    except Exception as e:
        logger.error(f"[❌] Error in handle_private_other_messages for user {message.from_user.id}: {e}") 

async def refund_command_handler(client: Client, message: Message) -> None:
    """Handle the /refund command (admin only)"""
    try:
        user_id = message.from_user.id
        
        # Check if the user is an admin
        if user_id != Config.ADMIN_ID:
            logger.warning(f"[⚠️] Non-admin user {user_id} tried to use /refund command")
            await message.reply_text(messages.ADMIN_ONLY_COMMAND, reply_markup=ReplyKeyboardRemove())
            return
            
        # Check if command has the correct format: /refund user_id payment_id
        command_parts = message.text.split(' ')
        if len(command_parts) != 3:
            await message.reply_text(messages.REFUND_USAGE, reply_markup=ReplyKeyboardRemove())
            return
            
        target_user_id = int(command_parts[1])
        payment_charge_id = command_parts[2]
        
        # Log the refund attempt
        logger.info(f"[💲] Admin {user_id} initiated refund for user {target_user_id}, charge ID: {payment_charge_id}")
        
        # Attempt to refund
        try:
            await client.refund_star_payment(target_user_id, payment_charge_id)
            await message.reply_text(messages.REFUND_SUCCESS(target_user_id), reply_markup=ReplyKeyboardRemove())
            logger.info(f"[✅] Refund successful for user {target_user_id}, charge ID: {payment_charge_id}")
        except Exception as e:
            await message.reply_text(messages.REFUND_FAILED(str(e)), reply_markup=ReplyKeyboardRemove())
            logger.error(f"[❌] Refund failed for user {target_user_id}, charge ID: {payment_charge_id}: {e}")
    
    except Exception as e:
        logger.error(f"[❌] Error handling refund command: {e}")
        await message.reply_text(messages.REFUND_ERROR, reply_markup=ReplyKeyboardRemove())

async def ban_command_handler(client: Client, message: Message) -> None:
    """Handle the /ban command (admin only)"""
    try:
        user_id = message.from_user.id
        
        # Check if the user is an admin
        if user_id != Config.ADMIN_ID:
            logger.warning(f"[⚠️] Non-admin user {user_id} tried to use /ban command")
            await message.reply_text(messages.ADMIN_ONLY_COMMAND, reply_markup=ReplyKeyboardRemove())
            return
            
        # Check if command has the correct format: /ban user_id reason
        command_parts = message.text.split(' ', 2)  # Split into max 3 parts
        if len(command_parts) < 3:
            await message.reply_text(messages.BAN_USAGE, reply_markup=ReplyKeyboardRemove())
            return
            
        try:
            target_user_id = int(command_parts[1])
        except ValueError:
            await message.reply_text(messages.BAN_USAGE, reply_markup=ReplyKeyboardRemove())
            return
            
        ban_reason = command_parts[2]
        
        # Log the ban attempt
        logger.info(f"[🚫] Admin {user_id} attempting to ban user {target_user_id} with reason: {ban_reason}")
        
        # Attempt to ban
        if db.ban_user(target_user_id, ban_reason):
            await message.reply_text(messages.BAN_SUCCESS(target_user_id, ban_reason), reply_markup=ReplyKeyboardRemove())
            logger.info(f"[✅] User {target_user_id} banned successfully by admin {user_id}")
        else:
            await message.reply_text(messages.BAN_ERROR, reply_markup=ReplyKeyboardRemove())
            logger.error(f"[❌] Failed to ban user {target_user_id}")
    
    except Exception as e:
        logger.error(f"[❌] Error handling ban command: {e}")
        await message.reply_text(messages.BAN_ERROR, reply_markup=ReplyKeyboardRemove())

async def unban_command_handler(client: Client, message: Message) -> None:
    """Handle the /unban command (admin only)"""
    try:
        user_id = message.from_user.id
        
        # Check if the user is an admin
        if user_id != Config.ADMIN_ID:
            logger.warning(f"[⚠️] Non-admin user {user_id} tried to use /unban command")
            await message.reply_text(messages.ADMIN_ONLY_COMMAND, reply_markup=ReplyKeyboardRemove())
            return
            
        # Check if command has the correct format: /unban user_id
        command_parts = message.text.split(' ')
        if len(command_parts) != 2:
            await message.reply_text(messages.UNBAN_USAGE, reply_markup=ReplyKeyboardRemove())
            return
            
        try:
            target_user_id = int(command_parts[1])
        except ValueError:
            await message.reply_text(messages.UNBAN_USAGE, reply_markup=ReplyKeyboardRemove())
            return
        
        # Log the unban attempt
        logger.info(f"[✅] Admin {user_id} attempting to unban user {target_user_id}")
        
        # Attempt to unban
        if db.unban_user(target_user_id):
            await message.reply_text(messages.UNBAN_SUCCESS(target_user_id), reply_markup=ReplyKeyboardRemove())
            logger.info(f"[✅] User {target_user_id} unbanned successfully by admin {user_id}")
        else:
            await message.reply_text(messages.USER_NOT_FOUND(target_user_id), reply_markup=ReplyKeyboardRemove())
            logger.warning(f"[⚠️] User {target_user_id} not found or already unbanned")
    
    except Exception as e:
        logger.error(f"[❌] Error handling unban command: {e}")
        await message.reply_text(messages.UNBAN_ERROR, reply_markup=ReplyKeyboardRemove()) 