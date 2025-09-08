from pyrogram import Client
from pyrogram.types import Message, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton, KeyboardButtonRequestChat, ChatPrivileges, InlineKeyboardMarkup, InlineKeyboardButton
from utils.logger import logger
from utils.cleanup import delete_scheduled_message, clean_up_tracking_info
from config.state import State
from config import messages
from utils.db import db
from config.config import Config
from utils.queue_manager import get_active_videos_count
from pyrogram.types import LinkPreviewOptions
from utils.decorators import combined_user_check, handle_errors

@combined_user_check
@handle_errors()
async def start_command_handler(client: Client, message: Message) -> None:
    """Handle the /start command"""
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    
    logger.info(f"[👋] New /start command from user {user_id} ({user_name})")
    
    # Check if user has a channel configured
    has_channel = db.has_user_channel(user_id)
    
    # Send appropriate welcome message based on channel setup
    if has_channel:
        welcome_text = messages.START_TEXT_EXISTING_USER
    else:
        welcome_text = messages.START_TEXT_NEW_USER
    
    await message.reply_text(welcome_text)

@combined_user_check
@handle_errors()
async def help_command_handler(client: Client, message: Message) -> None:
    """Handles the /help command"""
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    
    logger.info(f"[ℹ️] Received help command from user {user_id} ({user_name})")
    
    await message.reply_text(messages.HELP_TEXT)

@combined_user_check
@handle_errors()
async def cancel_command_handler(client: Client, message: Message) -> None:
    """Handles the /cancel command to cancel video processing"""
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    
    # Check if user has any active videos
    active_count = get_active_videos_count(user_id, is_channel=False)
    
    if active_count == 0 and user_id not in State.active_users:
        logger.info(f"[❌] User {user_id} ({user_name}) tried to cancel but has no active videos")
        await message.reply_text(messages.CANCEL_NO_ACTIVE_VIDEO)
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
        await message.reply_text(messages.CANCEL_NO_ACTIVE_VIDEO)
        return
    
    _, scheduled_msg_id, _, _, _ = State.video_info[transfer_msg_id]
    
    await delete_scheduled_message(scheduled_msg_id)
    clean_up_tracking_info(transfer_msg_id, user_id)
    
    # Check if user still has active videos AFTER cleanup
    remaining_count = get_active_videos_count(user_id, is_channel=False)
    
    if remaining_count > 0:
        # Keep user in active_users as they still have videos
        await message.reply_text(messages.CANCEL_STILL_ACTIVE(remaining_count))
    else:
        # Remove user from active_users
        State.active_users.discard(user_id)
        await message.reply_text(messages.CANCEL_SUCCESS)
        
    logger.info(f"[✅] Successfully canceled video processing for user {user_id} ({user_name}). Remaining videos: {remaining_count}")

@combined_user_check
@handle_errors()
async def handle_private_other_messages(client: Client, message: Message) -> None:
    """Handles non-video messages in private chats (catch-all)"""
    # Skip sending response for refunded payment messages
    if hasattr(message, 'refunded_payment'):
        return
    
    user_id = message.from_user.id
    await message.reply_text(messages.OTHER_MESSAGE_PROMPT)
    logger.info(f"[ℹ️] Sent response to user {user_id} for non-video message") 

@handle_errors(messages.REFUND_ERROR)
async def refund_command_handler(client: Client, message: Message) -> None:
    """Handle the /refund command (admin only)"""
    user_id = message.from_user.id
    
    # Check if the user is an admin
    if user_id != Config.ADMIN_ID:
        logger.warning(f"[⚠️] Non-admin user {user_id} tried to use /refund command")
        await message.reply_text(messages.ADMIN_ONLY_COMMAND)
        return
        
    # Check if command has the correct format: /refund user_id payment_id
    command_parts = message.text.split(' ')
    if len(command_parts) != 3:
        await message.reply_text(messages.REFUND_USAGE)
        return
        
    target_user_id = int(command_parts[1])
    payment_charge_id = command_parts[2]
    
    # Log the refund attempt
    logger.info(f"[💲] Admin {user_id} initiated refund for user {target_user_id}, charge ID: {payment_charge_id}")
    
    # Attempt to refund
    try:
        await client.refund_star_payment(target_user_id, payment_charge_id)
        await message.reply_text(messages.REFUND_SUCCESS(target_user_id))
        logger.info(f"[✅] Refund successful for user {target_user_id}, charge ID: {payment_charge_id}")
    except Exception as e:
        await message.reply_text(messages.REFUND_FAILED(str(e)))
        logger.error(f"[❌] Refund failed for user {target_user_id}, charge ID: {payment_charge_id}: {e}")

@handle_errors(messages.BAN_ERROR)
async def ban_command_handler(client: Client, message: Message) -> None:
    """Handle the /ban command (admin only)"""
    user_id = message.from_user.id
    
    # Check if the user is an admin
    if user_id != Config.ADMIN_ID:
        logger.warning(f"[⚠️] Non-admin user {user_id} tried to use /ban command")
        await message.reply_text(messages.ADMIN_ONLY_COMMAND)
        return
        
    # Check if command has the correct format: /ban user_id reason
    command_parts = message.text.split(' ', 2)  # Split into max 3 parts
    if len(command_parts) < 3:
        await message.reply_text(messages.BAN_USAGE)
        return
        
    try:
        target_user_id = int(command_parts[1])
    except ValueError:
        await message.reply_text(messages.BAN_USAGE)
        return
        
    ban_reason = command_parts[2]
    
    # Log the ban attempt
    logger.info(f"[🚫] Admin {user_id} attempting to ban user {target_user_id} with reason: {ban_reason}")
    
    # Attempt to ban
    if db.ban_user(target_user_id, ban_reason):
        await message.reply_text(messages.BAN_SUCCESS(target_user_id, ban_reason))
        logger.info(f"[✅] User {target_user_id} banned successfully by admin {user_id}")
    else:
        await message.reply_text(messages.BAN_ERROR)
        logger.error(f"[❌] Failed to ban user {target_user_id}")

@handle_errors(messages.UNBAN_ERROR)
async def unban_command_handler(client: Client, message: Message) -> None:
    """Handle the /unban command (admin only)"""
    user_id = message.from_user.id
    
    # Check if the user is an admin
    if user_id != Config.ADMIN_ID:
        logger.warning(f"[⚠️] Non-admin user {user_id} tried to use /unban command")
        await message.reply_text(messages.ADMIN_ONLY_COMMAND)
        return
        
    # Check if command has the correct format: /unban user_id
    command_parts = message.text.split(' ')
    if len(command_parts) != 2:
        await message.reply_text(messages.UNBAN_USAGE)
        return
        
    try:
        target_user_id = int(command_parts[1])
    except ValueError:
        await message.reply_text(messages.UNBAN_USAGE)
        return
    
    # Log the unban attempt
    logger.info(f"[✅] Admin {user_id} attempting to unban user {target_user_id}")
    
    # Attempt to unban
    if db.unban_user(target_user_id):
        await message.reply_text(messages.UNBAN_SUCCESS(target_user_id))
        logger.info(f"[✅] User {target_user_id} unbanned successfully by admin {user_id}")
    else:
        await message.reply_text(messages.USER_NOT_FOUND(target_user_id))
        logger.warning(f"[⚠️] User {target_user_id} not found or already unbanned")

@combined_user_check
@handle_errors()
async def channel_setup_command_handler(client: Client, message: Message) -> None:
    """Handle the /setchannel command to set up user's output channel"""
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    
    logger.info(f"[🔧] User {user_id} ({user_name}) requested channel setup")
    
    # Create keyboard with channel request button
    # Define required user privileges - user must be able to add bots
    user_admin_rights = ChatPrivileges(
        can_invite_users=True,  # Required to add bots to the channel
        can_manage_chat=True    # General admin privileges
    )
    
    request_chat_button = KeyboardButtonRequestChat(
        button_id=2,  # Different from premium system (which uses button_id=1)
        chat_is_channel=True,
        chat_is_created=False,  # Allow existing channels
        bot_is_member=False,    # Don't require bot to be member yet
        user_administrator_rights=user_admin_rights  # User must have rights to add bots
    )
    
    keyboard = ReplyKeyboardMarkup(
        [[KeyboardButton("📺 Select Channel", request_chat=request_chat_button)]],
        one_time_keyboard=True,
        is_persistent=True,
    )
    
    setup_text = messages.CHANNEL_SETUP_INSTRUCTIONS.format(bot_admin_link=Config.BOT_ADMIN_LINK)
    
    await message.reply_text(
        setup_text,
        reply_markup=keyboard,
        link_preview_options=LinkPreviewOptions(is_disabled=True)
    )

async def handle_channel_shared(client: Client, message: Message) -> None:
    """Handle when user shares a channel using the request chat button"""
    try:
        user_id = message.from_user.id
        user_name = message.from_user.first_name
        
        if not message.chat_shared:
            return
        
        # Only handle our button (button_id=2), not the premium system (button_id=1)
        if message.chat_shared.button_id != 2:
            return
        
        channel_id = message.chat_shared.chat.id
        
        logger.info(f"[📺] User {user_id} ({user_name}) shared channel {channel_id}")
        
        # Check if bot already has admin privileges in the channel
        try:
            bot_member = await client.get_chat_member(channel_id, (await client.get_me()).id)
            bot_status = str(bot_member.status).lower()
            
            # Check if bot is already admin with posting privileges
            if "administrator" in bot_status or "creator" in bot_status:
                has_post_permission = True
                if hasattr(bot_member, 'privileges') and bot_member.privileges:
                    has_post_permission = getattr(bot_member.privileges, 'can_post_messages', True)
                
                if has_post_permission:
                    # Bot already has the required permissions - complete setup immediately
                    if db.set_user_channel(user_id, channel_id):
                        await message.reply_text(
                            messages.CHANNEL_SETUP_SUCCESS,
                            reply_markup=ReplyKeyboardRemove()
                        )
                        logger.info(f"[✅] Channel setup completed immediately for user {user_id}, channel {channel_id} - bot already has permissions")
                    else:
                        await message.reply_text(
                            messages.CHANNEL_SETUP_ERROR,
                            reply_markup=ReplyKeyboardRemove()
                        )
                    return
        
        except Exception as e:
            # Bot is not in the channel or doesn't have permissions - continue with normal flow
            logger.info(f"[ℹ️] Bot not admin in channel {channel_id} or error checking: {e}")
        
        # Store channel temporarily until bot is added as admin
        State.pending_channel_setups[user_id] = channel_id
        
        # Ask user to add bot as admin with inline button
        inline_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🤖 Add Bot as Admin", url=Config.BOT_ADMIN_LINK)],
        ])
        
        await message.reply_text(
            messages.CHANNEL_SETUP_PENDING,
            reply_markup=inline_keyboard,
        )
        
    except Exception as e:
        logger.error(f"[❌] Error handling shared channel: {e}")
        await message.reply_text(messages.CHANNEL_SETUP_GENERAL_ERROR)

async def handle_chat_member_updated(client: Client, chat_member_updated) -> None:
    """Handle when bot's status in a chat is updated (e.g., added as admin)"""
    try:
        # Get bot info
        bot_user = await client.get_me()
        
        # Check if this is about our bot
        is_about_bot = False
        
        # Check if new_chat_member exists and is about our bot
        if chat_member_updated.new_chat_member and chat_member_updated.new_chat_member.user:
            if chat_member_updated.new_chat_member.user.id == bot_user.id:
                is_about_bot = True
        # Check if old_chat_member exists and is about our bot (for removal events)
        elif chat_member_updated.old_chat_member and chat_member_updated.old_chat_member.user:
            if chat_member_updated.old_chat_member.user.id == bot_user.id:
                is_about_bot = True
        
        if not is_about_bot:
            return
        
        # Get bot's old and new status
        old_status = chat_member_updated.old_chat_member.status if chat_member_updated.old_chat_member else None
        new_status = chat_member_updated.new_chat_member.status if chat_member_updated.new_chat_member else None
        channel_id = chat_member_updated.chat.id
        
        # Convert statuses to strings for comparison
        old_status_str = str(old_status).lower() if old_status else "none"
        new_status_str = str(new_status).lower() if new_status else "none"
        
        logger.info(f"[🔍] Bot status update: {old_status_str} -> {new_status_str} in chat {channel_id}")
        
        # Check if bot was removed
        # Case 1: new_chat_member is None (bot completely removed)
        # Case 2: new status indicates removal/restriction
        # Case 3: bot was admin but is no longer admin
        bot_was_removed = (
            chat_member_updated.new_chat_member is None or
            new_status is None or
            "left" in new_status_str or 
            "kicked" in new_status_str or
            "restricted" in new_status_str or
            (("administrator" in old_status_str or "creator" in old_status_str) and 
             "administrator" not in new_status_str and "creator" not in new_status_str)
        )
        
        if bot_was_removed:
            await handle_bot_removed_from_channel(client, channel_id)
            return
        
        # Handle bot being promoted to admin (channel setup)
        if "administrator" in new_status_str or "creator" in new_status_str:
            # Check if bot has posting privileges
            has_post_permission = True
            if hasattr(chat_member_updated.new_chat_member, 'privileges') and chat_member_updated.new_chat_member.privileges:
                has_post_permission = getattr(chat_member_updated.new_chat_member.privileges, 'can_post_messages', True)
            
            if not has_post_permission:
                # Bot was made admin but without posting privileges - treat as removal
                await handle_bot_removed_from_channel(client, channel_id)
                return
            
            # Find which user was waiting for this channel setup
            user_id = None
            is_premium_channel = False
            
            # Check regular channel setups first
            for pending_user_id, pending_channel_id in State.pending_channel_setups.items():
                if pending_channel_id == channel_id:
                    user_id = pending_user_id
                    is_premium_channel = False
                    break
            
            # If not found, check premium channel setups
            if not user_id:
                for pending_user_id, pending_channel_id in State.pending_premium_channel_setups.items():
                    if pending_channel_id == channel_id:
                        user_id = pending_user_id
                        is_premium_channel = True
                        break
            
            if not user_id:
                return
            
            # Handle regular channel setup
            if not is_premium_channel:
                # Store the channel in database and complete setup
                if db.set_user_channel(user_id, channel_id):
                    del State.pending_channel_setups[user_id]
                    await client.send_message(user_id, messages.CHANNEL_SETUP_SUCCESS, reply_markup=ReplyKeyboardRemove())
                    logger.info(f"[✅] Channel setup completed for user {user_id}, channel {channel_id}")
                else:
                    await client.send_message(user_id, messages.CHANNEL_SETUP_ERROR, reply_markup=ReplyKeyboardRemove())
            
            # Handle premium channel setup
            else:
                # Add premium channel to database
                if db.add_channel(channel_id, user_id):
                    del State.pending_premium_channel_setups[user_id]
                    
                    # Get current channel count for success message
                    existing_channels = db.get_user_channels(user_id)
                    current_channels = len(existing_channels) - 1  # Subtract 1 because we just added one
                    max_channels = db.get_max_channels(user_id)
                    
                    success_text = messages.channel_added_success_text(
                        channel_id=channel_id, current_channels=current_channels, max_channels=max_channels
                    )
                    await client.send_message(user_id, success_text, reply_markup=ReplyKeyboardRemove())
                    logger.info(f"[✅] Premium channel {channel_id} added for user {user_id} (slot {current_channels+1}/{max_channels})")
                else:
                    await client.send_message(user_id, messages.ERROR_ADDING_CHANNEL, reply_markup=ReplyKeyboardRemove())
                    logger.error(f"[❌] Failed to add premium channel {channel_id} for user {user_id}")
        
    except Exception as e:
        logger.error(f"[❌] Error handling chat member update: {e}")

async def handle_bot_removed_from_channel(client: Client, channel_id: int) -> None:
    """Handle when bot is removed from a channel or loses posting privileges"""
    try:
        # Find which user had this channel configured
        user_id = db.find_user_by_channel(channel_id)
        
        if not user_id:
            logger.info(f"[ℹ️] Bot removed from channel {channel_id} but no user had it configured")
            return
        
        # Remove the channel from user's configuration
        if db.remove_user_channel(user_id):
            # Notify user that they need to reconfigure
            await client.send_message(
                user_id,
                messages.CHANNEL_ACCESS_LOST,
            )
            logger.info(f"[🔄] Removed channel {channel_id} configuration for user {user_id} - bot was removed/restricted")
        
    except Exception as e:
        logger.error(f"[❌] Error handling bot removal from channel {channel_id}: {e}")

@handle_errors(messages.ADD_PREMIUM_ERROR)
async def add_premium_command_handler(client: Client, message: Message) -> None:
    """Handle the /add_premium command (admin only)"""
    user_id = message.from_user.id
    
    # Check if the user is an admin
    if user_id != Config.ADMIN_ID:
        logger.warning(f"[⚠️] Non-admin user {user_id} tried to use /add_premium command")
        await message.reply_text(messages.ADMIN_ONLY_COMMAND)
        return
        
    # Check if command has the correct format: /add_premium user_id months
    command_parts = message.text.split(' ')
    if len(command_parts) != 3:
        await message.reply_text(messages.ADD_PREMIUM_USAGE)
        return
        
    try:
        target_user_id = int(command_parts[1])
        months = int(command_parts[2])
    except ValueError:
        await message.reply_text(messages.ADD_PREMIUM_USAGE)
        return
    
    if months <= 0:
        await message.reply_text(messages.ADD_PREMIUM_INVALID_MONTHS)
        return
        
    # Log the premium addition attempt
    logger.info(f"[⭐] Admin {user_id} adding premium to user {target_user_id} for {months} months")
    
    # Add premium with basic plan (1 channel)
    if db.set_user_premium(target_user_id, is_premium=1, max_channels=1, months=months):
        await message.reply_text(messages.ADD_PREMIUM_SUCCESS(target_user_id, months))
        logger.info(f"[✅] Premium added successfully for user {target_user_id} for {months} months")
        
        # Notify the user about their new premium status
        try:
            await client.send_message(
                target_user_id, 
                messages.PREMIUM_GRANTED_NOTIFICATION(months)
            )
            logger.info(f"[📨] Premium notification sent to user {target_user_id}")
        except Exception as notify_error:
            logger.warning(f"[⚠️] Could not notify user {target_user_id} about premium: {notify_error}")
    else:
        await message.reply_text(messages.ADD_PREMIUM_ERROR)
        logger.error(f"[❌] Failed to add premium for user {target_user_id}") 