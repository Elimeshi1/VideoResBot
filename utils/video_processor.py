"""
Video processing module for the Telegram Video Quality Bot.

This module handles video processing functionality:
- Scheduling videos for processing
- Tracking video processing progress
- Handling processed videos with alternative qualities
"""
from datetime import datetime, timezone, timedelta
from pyrogram.types import Message, InputMediaVideo
from config.state import State
from config.config import Config
from utils.logger import logger
from utils.video_utils import calculate_processing_time, format_video_info
from utils.cleanup import delete_scheduled_message, clean_up_tracking_info


async def schedule_video_to_destination(transfer_msg_id: int) -> int | None:
    """Schedule video to destination channel and store mapping."""
    try:
        logger.info(f"[🔄] Scheduling video {transfer_msg_id} to destination channel...")
        if not Config.DESTINATION_CHANNEL or not Config.TRANSFER_CHANNEL:
             logger.error("[❌] DESTINATION_CHANNEL or TRANSFER_CHANNEL not configured.")
             return None
        schedule_time = datetime.now(timezone.utc) + timedelta(days=365) 
        scheduled_msg = await State.userbot.copy_message(
            Config.DESTINATION_CHANNEL, 
            Config.TRANSFER_CHANNEL, 
            transfer_msg_id,
            schedule_date=schedule_time
        )
        scheduled_msg_id = scheduled_msg.id
        logger.info(f"[✅] Scheduled message created with ID: {scheduled_msg_id}")
        
        State.scheduled_to_transfer_map[scheduled_msg_id] = transfer_msg_id
        logger.info(f"[🗺️] Stored mapping: Scheduled ID {scheduled_msg_id} -> Transfer ID {transfer_msg_id}")
        
        return scheduled_msg_id
    except Exception as e:
         logger.error(f"[❌] Failed to schedule video {transfer_msg_id}: {e}")
         return None

async def track_video_progress(transfer_msg_id: int, user_id: int, scheduled_msg_id: int, original_size: int, duration: int, channel_data=None) -> None:
    """Save tracking information for video processing in State"""
    current_time = datetime.now()
    logger.info(f"[📊] Tracking video progress for Transfer ID: {transfer_msg_id}, User/Channel: {user_id if not channel_data else channel_data}")
    # Store main video info keyed by transfer_msg_id
    State.video_info[transfer_msg_id] = (user_id, scheduled_msg_id, current_time, original_size, duration)
    
    # Store reverse mapping (user/channel -> transfer_id) for potential lookups
    if channel_data:
        # For channel videos, store tuple of (channel_id, message_id)
        State.user_videos[transfer_msg_id] = channel_data
    else:
        # For user videos, store user_id
        State.user_videos[transfer_msg_id] = user_id


async def send_original_video(msg: Message, user_id: int) -> bool:
    """Send the original video quality back to the user."""
    try:
        # Caption with original quality info and hint about settings button
        original_caption = f"Original quality: {msg.video.height}p\n\nℹ️ You can also tap on the video settings button to select different qualities!"
        await msg.copy(user_id, caption=original_caption)
        logger.info(f"[✅] Sent original video ({msg.video.height}p) to user {user_id}")
        return True
    except Exception as e:
        logger.error(f"[❌] Failed to send original video to user {user_id}: {e}")
        return False

async def send_alternative_videos(msg: Message, user_id: int) -> int:
    """Send available alternative video qualities back to the user."""
    sent_count = 0
    if not msg.video or not msg.video.alternative_videos:
         logger.info(f"[ℹ️] No video or alternative videos found for message {msg.id}")
         return 0
         
    logger.info(f"[ℹ️] Found {len(msg.video.alternative_videos)} alternative videos for message {msg.id}")
    try:
        for i, video in enumerate(msg.video.alternative_videos): 
            if i % 2 == 1:
                continue
                
            try:
                quality = f"{video.height}p" if video.height else f"Alternative {i+1}"
                caption = f"📹 {quality}"
                await State.bot.send_video(
                    user_id,
                    video.file_id,
                    caption=caption
                )
                sent_count += 1
                logger.info(f"[✅] Sent {quality} video to user {user_id}")
            except Exception as send_err:
                quality_label = f"{video.height}p" if video.height else f"#{i+1}"
                logger.error(f"[❌] Failed to send alternative video {quality_label} to user {user_id}: {send_err}")
        return sent_count
    except Exception as e:
        logger.error(f"[❌] Error iterating or sending alternative videos for user {user_id}: {e}")
        return sent_count # Return count sent so far

async def handle_processed_video(transfer_msg_id: int, processed_junk_msg: Message) -> None:
    """Handles a video confirmed as processed via Junk Channel polling."""
    logger.info(f"[🏁] Handling processed video confirmed via polling. Transfer ID: {transfer_msg_id}, Junk Msg ID: {processed_junk_msg.id}")
    # --- Retrieve original tracking info --- 
    if transfer_msg_id not in State.video_info:
        logger.warning(f"[⚠️] Tracking info for Transfer ID {transfer_msg_id} disappeared before processed handler could run. Aborting.")
        scheduled_id_found = None
        for s_id, t_id in State.scheduled_to_transfer_map.items():
             if t_id == transfer_msg_id:
                  scheduled_id_found = s_id
                  break
        if scheduled_id_found:
             try:
                  del State.scheduled_to_transfer_map[scheduled_id_found]
                  logger.info(f"[🧹] Cleaned orphaned map entry for Scheduled ID {scheduled_id_found}")
             except KeyError:
                  pass
        return

    user_id, scheduled_msg_id, timestamp, original_size, duration = State.video_info[transfer_msg_id]
    user_or_channel_data = State.user_videos.get(transfer_msg_id)
    is_channel_post = isinstance(user_or_channel_data, tuple)
    
    # --- Ensure we have the necessary message data --- 
    if not processed_junk_msg.video:
         logger.error(f"[❌] Junk message {processed_junk_msg.id} for TID {transfer_msg_id} has no video object. Cannot proceed.")
         # Attempt cleanup as something is wrong
         await delete_scheduled_message(scheduled_msg_id) 
         clean_up_tracking_info(transfer_msg_id, user_or_channel_data)
         return
         
    sent_original = False
    sent_alternatives = 0
    edit_successful = False # Flag for channel edit status

    # --- Perform action based on source (User or Channel) --- 
    if is_channel_post:
         channel_id, original_msg_id = user_or_channel_data
         logger.info(f"[📢] Processed video (TID: {transfer_msg_id}) corresponds to channel post: {channel_id}/{original_msg_id}")
         # Edit the original channel message using the processed_junk_msg
         try:
             await edit_channel_message_with_processed_video(channel_id, original_msg_id, processed_junk_msg)
             edit_successful = True # Assume success if no exception
         except Exception as e:
              logger.error(f"[❌] Failed to edit channel message {original_msg_id} in {channel_id} using junk msg {processed_junk_msg.id}: {e}")
              # Proceed to reporting/cleanup even if edit fails
    else:
         # User video: Send results back to user using the processed_junk_msg
         logger.info(f"[👤] Processed video (TID: {transfer_msg_id}) corresponds to user: {user_id}")
         try:
             # Use the junk message to send videos back
             sent_original = await send_original_video(processed_junk_msg, user_id)
             sent_alternatives = await send_alternative_videos(processed_junk_msg, user_id)
             logger.info(f"[ℹ️] User {user_id} (Processed): Sent {sent_alternatives} alternative videos and original: {sent_original}")
         except Exception as e:
             logger.error(f"[❌] Error sending processed videos back to user {user_id} (TID: {transfer_msg_id}): {e}")
             # Continue to reporting and cleanup

    # --- Reporting --- 
    try:
        processing_time_min = (datetime.now() - timestamp).total_seconds() / 60
        # Use height from the processed junk message
        estimated_time_min = calculate_processing_time(duration, processed_junk_msg.video.height)
        
        qualities_sent_count = 0
        if not is_channel_post:
             qualities_sent_count = sent_alternatives + (1 if sent_original else 0)
        
        status_text = format_video_info(
            original_size,
            duration,
            processing_time_min,
            estimated_time_min,
            qualities_sent_count 
        )
        
        if is_channel_post:
             status_text += f" (Edit {'Succeeded' if edit_successful else 'Failed'})"
             
        user_channel_info = f"👤 User ID: {user_id}" if not is_channel_post else f"📺 Channel: {channel_id}/{original_msg_id}"
        admin_report = f"{user_channel_info}\n\n{status_text}"
        
        await State.bot.send_message(Config.ADMIN_ID, admin_report)
        logger.info(f"[✅] Sent processing report to admin for Transfer ID: {transfer_msg_id}")

    except Exception as report_err:
        logger.error(f"[❌] Error calculating/sending admin report for {transfer_msg_id}: {report_err}")
        
    # --- Cleanup (ALWAYS runs) --- 
    finally:
        logger.info(f"[🧹] Starting final cleanup for Transfer ID: {transfer_msg_id} after polling detection.")
        try:
            # 1. Delete the ORIGINAL scheduled message in destination channel (using its retrieved ID)
            if scheduled_msg_id:
                 await delete_scheduled_message(scheduled_msg_id)
            else:
                 logger.warning(f"[⚠️] Cannot delete scheduled message for TID {transfer_msg_id} as scheduled_msg_id was not found in tracking info.")
            
            # 2. Clean up tracking info using the original user/channel data
            clean_up_tracking_info(transfer_msg_id, user_or_channel_data)
            
        except Exception as cleanup_err:
            logger.error(f"[❌] Error during final cleanup for {transfer_msg_id} after polling: {cleanup_err}")

async def handle_video_timeout(transfer_msg_id: int, user_id: int, scheduled_msg_id: int, timestamp: datetime) -> None:
    """Handles a video that has timed out based on tracking info in State."""
    
    logger.warning(f"[⏰] Handling timeout for Transfer ID: {transfer_msg_id}")
    if transfer_msg_id not in State.video_info:
        logger.error(f"[❌] Timeout triggered for unknown Transfer ID: {transfer_msg_id}")
        # Attempt to clean potentially orphaned user_videos entry
        clean_up_tracking_info(transfer_msg_id, State.user_videos.get(transfer_msg_id))
        return

    user_or_channel_data = State.user_videos.get(transfer_msg_id)
    is_channel_post = isinstance(user_or_channel_data, tuple)
    time_diff_min = (datetime.now() - timestamp).total_seconds() / 60

    try:
        if is_channel_post:
            channel_id, original_msg_id = user_or_channel_data
            logger.warning(f"[⏰] Channel video {channel_id}/{original_msg_id} (Transfer ID: {transfer_msg_id}) timed out after {time_diff_min:.1f} mins")
            await State.bot.send_message(Config.ADMIN_ID, f"⏰ Channel video timeout: {channel_id}/{original_msg_id} (TID: {transfer_msg_id}) after {time_diff_min:.1f} mins.")
        else:
            # User video
            logger.warning(f"[⏰] User video {user_id} (Transfer ID: {transfer_msg_id}) timed out after {time_diff_min:.1f} mins")
            timeout_message = (
                f"⏰ **Processing Timeout**\n\n"
                f"Your video processing timed out after {time_diff_min:.1f} minutes.\n"
                f"This might be due to a file issue or high load.\n\n"
            )
            await State.bot.send_message(user_id, timeout_message)
            # Also notify admin
            await State.bot.send_message(Config.ADMIN_ID, f"⏰ User video timeout: {user_id} (TID: {transfer_msg_id}) after {time_diff_min:.1f} mins.")

    except Exception as notify_err:
        logger.error(f"[❌] Error notifying user/admin about timeout for {transfer_msg_id}: {notify_err}")
    finally:
        # Always attempt cleanup
        try:
            await delete_scheduled_message(scheduled_msg_id)
            clean_up_tracking_info(transfer_msg_id, user_or_channel_data)
        except Exception as cleanup_err:
            logger.error(f"[❌] Error during cleanup after timeout for {transfer_msg_id}: {cleanup_err}")

async def edit_channel_message_with_processed_video(channel_id: int, message_id: int, processed_msg: Message) -> None:
    """Edits the original channel message with the processed video that has alternative qualities"""
    try:
        # Ensure processed_msg has a video object before proceeding
        if not processed_msg.video:
             logger.error(f"[❌] Processed message {processed_msg.id} is missing the video object. Cannot edit channel message {message_id}.")
             return
             
        logger.info(f"[🔄] Attempting to edit channel message {message_id} in channel {channel_id} with processed video {processed_msg.id}")
        
        # Get original message info (Use bot client to get message from channel)
        original_msg = await State.bot.get_messages(channel_id, message_id)
        if not original_msg:
            logger.error(f"[❌] Failed to get original message {message_id} from channel {channel_id}")
            return
            
        # Keep original caption if it exists
        caption = original_msg.caption or ""
        
        # Create InputMediaVideo object for editing using the processed message's file_id
        media = InputMediaVideo(
            media=processed_msg.video.file_id,
            caption=caption,
            # Use caption_entities from the original message if they exist
            caption_entities=original_msg.caption_entities if original_msg.caption_entities else None 
        )
        
        # Edit the message
        await State.bot.edit_message_media(
            chat_id=channel_id,
            message_id=message_id,
            media=media
        )
        
        logger.info(f"[✅] Successfully edited channel message {message_id} in {channel_id}")
            
    except Exception as e:
        logger.error(f"[❌] Failed to edit channel message {message_id} in {channel_id}: {e}")

async def forward_to_transfer_channel(message: Message) -> Message | None:
    """Forward video message to the configured transfer channel."""
    try:
        if not Config.TRANSFER_CHANNEL:
            logger.error("[❌] TRANSFER_CHANNEL not configured.")
            return None
        transfer_msg = await message.forward(Config.TRANSFER_CHANNEL)
        logger.info(f"[➡️] Forwarded message {message.id} to transfer channel. New message ID: {transfer_msg.id}")
        return transfer_msg
    except Exception as e:
        logger.error(f"[❌] Failed to forward message {message.id} to transfer channel: {e}")
        return None
