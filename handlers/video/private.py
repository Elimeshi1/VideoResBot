"""
Private chat video handler module.

This module handles videos sent by users in private chats.
"""

from pyrogram import Client
from pyrogram.types import Message, ReplyKeyboardRemove
from utils.logger import logger
from utils.video_utils import calculate_processing_time
from config.state import State
from config.config import Config
from utils.db import db
from utils.cleanup import cleanup_and_process_next
from utils.queue_manager import (
    increment_active_videos,
    get_active_videos_count,
    add_to_queue
)

from utils.video_utils import (
    check_video_size,
    check_video_codec_format
)
from utils.video_processor import (
    schedule_video_to_destination,
    track_video_progress,
    send_original_video,
    send_alternative_videos,
    format_video_info,
    forward_to_transfer_channel
)
from config import messages

async def check_video_requirements(message: Message, status_message: Message) -> tuple[bool, Message]:
    """Checks if the video meets all requirements for private chats"""
    user_id = message.from_user.id
    
    # Check if queue is full
    if len(State.video_info) >= Config.MAX_QUEUED_VIDEOS:
        logger.info(f"[⚠️] Video queue is full. Current size: {len(State.video_info)}")
        await status_message.edit_text(messages.SYSTEM_BUSY)
        return False, status_message
    
    # Check video size
    if not await check_video_size(message.video, f"from user {user_id}"):
        await status_message.edit_text(messages.VIDEO_TOO_LARGE(Config.MAX_VIDEO_SIZE_GB))
        return False, status_message
    
    return True, status_message

async def check_video_format(message: Message, status_message: Message) -> tuple[bool, Message]:
    """Checks if the video format and codec are supported"""
    user_id = message.from_user.id
    
    # Update status message for codec check
    await status_message.edit_text(messages.CHECKING_FORMAT)
    
    # Check video codec and format
    result = await check_video_codec_format(message.video, f"for user {user_id}")
    if not result:
        await status_message.edit_text(messages.UNSUPPORTED_CODEC)
        return False, status_message
    
    return True, status_message

async def process_video_handler(client: Client, message: Message) -> None:
    """Handles video messages from users in private chats"""
    try:
        user_id = message.from_user.id
        user_name = message.from_user.first_name
        
        # Check if user is banned
        is_banned, ban_reason = db.is_user_banned(user_id)
        if is_banned:
            logger.warning(f"[🚫] Banned user {user_id} ({user_name}) attempted to send video")
            await message.reply_text(messages.USER_BANNED(ban_reason), reply_markup=ReplyKeyboardRemove())
            return
        
        # Check if user has configured a channel
        if not db.has_user_channel(user_id):
            logger.info(f"[📺] User {user_id} ({user_name}) needs to set up channel first")
            await message.reply_text(
                messages.CHANNEL_SETUP_REQUIRED,
                reply_markup=ReplyKeyboardRemove()
            )
            return
        
        if user_id in State.active_users:
            user_has_active_entry = any(
                isinstance(uid, int) and uid == user_id and tid in State.video_info
                for tid, uid in State.user_videos.items()
            )
            if not user_has_active_entry:
                logger.warning(f"[🧹] User {user_id} was in active_users but had no corresponding entry in user_videos/video_info. Cleaning up stale entry.")
                State.active_users.discard(user_id)
        
        # Send immediate acknowledgment message
        status_message = await message.reply_text(messages.VIDEO_RECEIVED)
        
        # Initialize database for premium check
        is_premium = db.is_user_premium(user_id)
        
        # Check active videos count using the new State method
        active_videos_count = get_active_videos_count(user_id, is_channel=False)
        
        # Check if user already has maximum allowed videos in processing
        max_concurrent_videos = Config.MAX_CONCURRENT_VIDEOS_PREMIUM if is_premium else Config.MAX_CONCURRENT_VIDEOS_REGULAR
        if active_videos_count >= max_concurrent_videos:
            logger.info(f"[⚠️] User {user_id} ({user_name}) already has {active_videos_count} active videos in processing (max: {max_concurrent_videos})")
            
            # Add to queue FIRST, then get position
            add_to_queue(message, user_id, is_channel=False)
            queued_position = len(State.user_video_queue[user_id])
            
            await status_message.edit_text(
                messages.QUEUE_LIMIT_REACHED(queued_position, is_premium, Config.MAX_CONCURRENT_VIDEOS_PREMIUM)
            ) 
            return
            
        # If all checks passed, mark as active and increment counter
        State.active_users.add(user_id)
        increment_active_videos(user_id, is_channel=False)
        
        try:
            # Forward to transfer channel
            logger.info(f"[📩] Received video from user {user_id} ({user_name})")
            transfer_msg = await forward_to_transfer_channel(message)
            if not transfer_msg:
                 await status_message.edit_text(messages.FAILED_INITIATE_PROCESS)
                 await cleanup_and_process_next(user_id, is_channel=False)
                 return
            transfer_msg_id = transfer_msg.id
            
            if transfer_msg.video and transfer_msg.video.alternative_videos:
                logger.info(f"[⚡️] Video (Transfer ID: {transfer_msg_id}) was instantly processed by Telegram (found alternative_videos). Sending results directly.")
                try:
                    sent_original = await send_original_video(transfer_msg, user_id)
                    sent_alternatives = await send_alternative_videos(transfer_msg, user_id)
                    logger.info(f"[ℹ️] User {user_id} (Instant): Sent {sent_alternatives} alternative videos and original: {sent_original}")

                    # Send Admin Report
                    try:
                        qualities_sent_count = sent_alternatives + (1 if sent_original else 0)
                        status_text = format_video_info(
                            message.video.file_size,
                            message.video.duration,
                            0, # Processing time is negligible
                            0, # Estimated time irrelevant
                            qualities_sent_count 
                        )
                        admin_report = (f"⚡️ Video Instantly Processed\n\n"
                                        f"👤 User ID: {user_id}\n"
                                        f"{status_text}")
                        await State.bot.send_message(Config.ADMIN_ID, admin_report)
                        logger.info(f"[✅] Sent instant processing report to admin for Transfer ID: {transfer_msg_id}")
                    except Exception as report_err:
                        logger.error(f"[❌] Error sending admin report for instant video {transfer_msg_id}: {report_err}")

                except Exception as send_err:
                     logger.error(f"[❌] Error sending instantly processed videos for Transfer ID {transfer_msg_id} to user {user_id}: {send_err}")
                finally:
                    # Cleanup state for this user and exit
                    await cleanup_and_process_next(user_id, is_channel=False)
                    return
            
            # Check if video meets requirements before proceeding
            is_valid, status_message = await check_video_requirements(message, status_message)
            if not is_valid:
                # Cleanup state since requirements check failed
                await cleanup_and_process_next(user_id, is_channel=False)
                return
                
            # Check format AFTER requirements
            is_valid, status_message = await check_video_format(message, status_message)
            if not is_valid:
                # Cleanup state since format check failed
                await cleanup_and_process_next(user_id, is_channel=False)
                return
            
            # Schedule to destination channel
            scheduled_msg_id = await schedule_video_to_destination(transfer_msg_id)
            if not scheduled_msg_id:
                await status_message.edit_text(messages.FAILED_SCHEDULE_PROCESS)
                await cleanup_and_process_next(user_id, is_channel=False)
                return
                
            # Update message with processing info
            estimated_time = calculate_processing_time(message.video.duration, message.video.height)
            await status_message.edit_text(
                messages.PROCESSING_VIDEO(estimated_time)
            )
            
            # Track progress ONLY after successful scheduling
            await track_video_progress(
                transfer_msg_id,
                user_id,
                scheduled_msg_id,
                message.video.file_size,
                message.video.duration
            )
            
            logger.info(f"[✅] Video from user {user_id} forwarded. Transfer ID: {transfer_msg_id}, Scheduled ID: {scheduled_msg_id}")
            
        except Exception as e:
            logger.error(f"[❌] Error processing video from user {user_id}: {e}")
            await status_message.edit_text(messages.INTERNAL_PROCESS_ERROR)
            await cleanup_and_process_next(user_id, is_channel=False)
            return
            
    except Exception as e:
        # General error handler for the entire process
        user_id = message.from_user.id if message.from_user else "unknown"
        logger.error(f"[❌] Top-level error processing video from user {user_id}: {e}", exc_info=True)
        try:
            # Use the status_message if available, otherwise reply to original message
            msg_to_reply = status_message if 'status_message' in locals() else message
            await msg_to_reply.reply_text(messages.CRITICAL_PROCESS_ERROR)
        except Exception as nested_e:
            logger.error(f"[❌] Error sending critical error message: {nested_e}")
        finally:
            # Ensure user is removed from active set and decrement counter in case of any error
            if message.from_user:
                await cleanup_and_process_next(message.from_user.id, is_channel=False)
            # Attempt cleanup if tracking might have started
            if 'transfer_msg_id' in locals() and 'user_id' in locals() and transfer_msg_id and user_id:
                from utils.cleanup import clean_up_tracking_info
                try:
                    # Need to pass user_id for cleanup in this case
                    clean_up_tracking_info(transfer_msg_id, user_id) 
                except Exception as cleanup_error:
                    logger.error(f"[❌] Error during final cleanup attempt: {cleanup_error}")

def remove_user_from_active_if_no_videos(user_id: int):
    """Removes user from State.active_users only if they have no active videos left."""
    if not any(
        isinstance(uid, int) and uid == user_id and tid in State.video_info
        for tid, uid in State.user_videos.items()
    ):
        State.active_users.discard(user_id) 