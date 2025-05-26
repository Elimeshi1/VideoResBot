from utils.logger import logger
from config.state import State
from config.config import Config
import asyncio
from datetime import datetime
from utils.queue_manager import (
    decrement_active_videos,
    get_active_videos_count,
    has_queued_videos,
    get_next_from_queue
)
from utils.video_utils import is_userbot_connected


async def delete_scheduled_message(scheduled_msg_id: int) -> None:
    """Deletes a scheduled message from the destination channel"""
    try:
        # Ensure userbot is available and connected
        if State.userbot and await is_userbot_connected(State.userbot):
            await State.userbot.delete_messages(
                chat_id=Config.DESTINATION_CHANNEL, 
                message_ids=scheduled_msg_id,
                is_scheduled=True
            )
            logger.info(f"[🗑️] Deleted scheduled message {scheduled_msg_id}")
        else:
             logger.warning(f"Userbot not available, cannot delete scheduled message {scheduled_msg_id}")
    except Exception as e:
        # Catch specific errors if needed, e.g., MessageIdInvalid
        logger.error(f"[❌] Error deleting scheduled message {scheduled_msg_id}: {e}")

def clean_up_tracking_info(transfer_msg_id: int, user_or_channel_data: int | tuple | None) -> None:
    """Cleans up tracking information for a video (video_info, user_videos, active_users). 
       Also attempts to clean the scheduled_to_transfer_map if possible.
       Checks the queue for the next video to process.
    """
    if not transfer_msg_id:
        logger.warning("[⚠️] Attempted to clean up with invalid transfer_msg_id.")
        return
        
    # Determine user_id for active_users cleanup
    user_id_for_cleanup = -1 # Default to channel/unknown
    is_channel = False
    channel_id = None
    
    if isinstance(user_or_channel_data, int):
        user_id_for_cleanup = user_or_channel_data
    elif isinstance(user_or_channel_data, tuple):
        # It's a channel video: (channel_id, message_id)
        is_channel = True
        channel_id = user_or_channel_data[0]
    # If user_or_channel_data is None, user_id_for_cleanup remains -1

    # 1. Remove from video_info (primary tracking)
    scheduled_msg_id = None
    if transfer_msg_id in State.video_info:
        _, scheduled_msg_id, _, _, _ = State.video_info.pop(transfer_msg_id)
        logger.info(f"[🧹] Removed transfer ID {transfer_msg_id} from video_info.")
    else:
        logger.warning(f"[⚠️] Transfer ID {transfer_msg_id} not found in video_info during cleanup.")

    # 2. Remove from user_videos (reverse map)
    if transfer_msg_id in State.user_videos:
        State.user_videos.pop(transfer_msg_id)
        logger.info(f"[🧹] Removed transfer ID {transfer_msg_id} from user_videos.")
    
    # 3. Remove from active_users (only if it was a user video)
    if user_id_for_cleanup != -1 and not is_channel:
        # Decrement active videos count for user
        decrement_active_videos(user_id_for_cleanup, is_channel=False)
        
        # Only remove from active_users if there are no more active videos
        remaining_count = get_active_videos_count(user_id_for_cleanup, is_channel=False)
        if remaining_count == 0 and not has_queued_videos(user_id_for_cleanup, is_channel=False):
            State.active_users.discard(user_id_for_cleanup)
            logger.info(f"[🧹] Discarded user ID {user_id_for_cleanup} from active_users (no more active or queued videos).")
        else:
            logger.info(f"[🧹] Decremented active videos count for user {user_id_for_cleanup}. Remaining active: {remaining_count}")
    elif is_channel and channel_id:
        # Decrement active videos count for channel
        decrement_active_videos(channel_id, is_channel=True)
        logger.info(f"[🧹] Decremented active videos count for channel {channel_id}.")
        
    # 4. Attempt to clean up scheduled_to_transfer_map if we found the scheduled_msg_id
    if scheduled_msg_id and scheduled_msg_id in State.scheduled_to_transfer_map:
         # Double check if the mapping still points to the transfer_id we are cleaning
         if State.scheduled_to_transfer_map[scheduled_msg_id] == transfer_msg_id:
              try:
                   del State.scheduled_to_transfer_map[scheduled_msg_id]
                   logger.info(f"[🧹] Removed mapping for Scheduled ID: {scheduled_msg_id} from scheduled_to_transfer_map.")
              except KeyError:
                   pass
         else:
              logger.warning(f"[⚠️] Mismatch in scheduled_to_transfer_map cleanup: Scheduled ID {scheduled_msg_id} maps to a different Transfer ID than {transfer_msg_id}.")
    elif scheduled_msg_id:
         logger.warning(f"[⚠️] Scheduled ID {scheduled_msg_id} (from video_info) not found in scheduled_to_transfer_map during cleanup.")

    logger.info(f"[🧹] Cleanup tracking complete for Transfer ID {transfer_msg_id}.")
    
    # 5. Process next video from queue if any
    entity_id = user_id_for_cleanup if not is_channel else channel_id
    if entity_id and entity_id != -1:
        # Schedule task to process next video from queue
        if State.main_event_loop:
            State.main_event_loop.create_task(process_next_from_queue(entity_id, is_channel))
        else:
            logger.warning(f"[⚠️] Cannot schedule next video from queue: main_event_loop not available")

async def process_next_from_queue(entity_id: int, is_channel: bool = False) -> None:
    """Process the next video from the queue for a user or channel."""
    next_video = get_next_from_queue(entity_id, is_channel)
    if not next_video:
        logger.info(f"[🔄] No videos in queue for {'channel' if is_channel else 'user'} {entity_id}")
        return
        
    # Log that we're processing from queue
    logger.info(f"[🔄] Processing next video from queue for {'channel' if is_channel else 'user'} {entity_id}")
    
    try:
        if is_channel:
            from handlers.video.channel import process_channel_video
            await process_channel_video(next_video)
        else:
            from handlers.video.private import process_video_handler
            await process_video_handler(State.bot, next_video)
    except Exception as e:
        logger.error(f"[❌] Error processing next video from queue for {'channel' if is_channel else 'user'} {entity_id}: {e}")

async def cleanup_scheduled_messages() -> None:
    """Deletes all remaining scheduled messages during shutdown."""
    # This is called during shutdown, uses the remaining video_info
    if not State.video_info:
        logger.info("[🧹] No remaining scheduled messages to clean up during shutdown.")
        return
        
    logger.info(f"[🧹] Cleaning up {len(State.video_info)} remaining scheduled messages during shutdown...")
    
    # Create a copy to avoid modification during iteration (though cleanup removes items)
    items_to_cleanup = list(State.video_info.items()) 
    
    for transfer_msg_id, (user_id, scheduled_msg_id, _, _, _) in items_to_cleanup:
        # Attempt to delete the message
        await delete_scheduled_message(scheduled_msg_id)
        user_or_channel_data = State.user_videos.get(transfer_msg_id) 
        clean_up_tracking_info(transfer_msg_id, user_or_channel_data)
    
    logger.info("[✅] Shutdown cleanup of scheduled messages completed.")

async def run_periodic_cleanup_task():
    """Periodically checks for timed-out videos and polls scheduled videos by copying to Junk Channel."""
    # Import here to avoid circular dependency
    from utils.video_processor import handle_processed_video
    
    logger.info("Starting periodic video status check/polling task...")
    while True:
        try:
            await asyncio.sleep(Config.CHECK_INTERVAL) 
            
            videos_to_check = list(State.video_info.items()) # Check a snapshot
            
            if not videos_to_check:
                continue

            logger.info(f"[⏰] Polling/Checking status for {len(videos_to_check)} tracked videos...")

            for transfer_msg_id, (user_or_channel, scheduled_msg_id, timestamp, _, _) in videos_to_check:
                # Ensure scheduled_msg_id is valid
                if not scheduled_msg_id:
                    logger.warning(f"[⚠️] Skipping check for TID {transfer_msg_id} due to missing scheduled_msg_id in tracking info.")
                    continue
                    
                # 1. Check for Timeout
                if await check_video_timeout(transfer_msg_id, user_or_channel, scheduled_msg_id, timestamp):
                    continue

                # 2. Poll by copying to Junk Channel (if not timed out)
                junk_msg = None
                try:
                    logger.debug(f"[🔄] Polling TID {transfer_msg_id}: Copying original msg {transfer_msg_id} from Transfer Channel {Config.TRANSFER_CHANNEL} to Junk Channel {Config.JUNK_CHANNEL}")
                    if State.bot:
                        junk_msg = await State.bot.copy_message(
                            chat_id=Config.JUNK_CHANNEL,
                            from_chat_id=Config.TRANSFER_CHANNEL,
                            message_id=transfer_msg_id
                        )
                        logger.debug(f"[🗑️] Copied msg {transfer_msg_id} from Transfer Channel to Junk Channel. New msg ID: {junk_msg.id}")
                    else:
                        logger.warning(f"[⚠️] Userbot not available for polling TID {transfer_msg_id}")
                        continue # Skip polling if bot is down
                        
                except Exception as copy_err:
                    logger.error(f"[❌] Error copying msg {transfer_msg_id} from Transfer Channel to junk channel for polling TID {transfer_msg_id}: {copy_err}")
                    continue # Move to next video
                
                # 3. Check the Junk Message for alternatives
                if junk_msg and junk_msg.video.alternative_videos:                    
                    try:
                         # Make sure the state hasn't been cleaned up concurrently
                         if transfer_msg_id in State.video_info:
                              await handle_processed_video(transfer_msg_id, junk_msg) # Pass junk_msg
                         else:
                              logger.info(f"[ℹ️] Video {transfer_msg_id} was cleaned up before polling result could be processed.")
                    except Exception as handle_err:
                         logger.error(f"[❌] Error calling handle_processed_video for TID {transfer_msg_id} after polling: {handle_err}")

        except asyncio.CancelledError:
            logger.info("[⏰] Periodic video polling task cancelled.")
            break # Exit the loop if cancelled
        except Exception as e:
            logger.error(f"[❌] Error in periodic polling task: {e}", exc_info=True)
            # Wait a bit longer before retrying after an error
            await asyncio.sleep(Config.CHECK_INTERVAL * 2) 

async def check_video_timeout(transfer_msg_id: int, user_id: int, scheduled_msg_id: int, timestamp: datetime) -> bool:
    """Checks if a video has timed out and handles it if necessary"""
    current_time = datetime.now()
    time_diff = (current_time - timestamp).total_seconds()
    
    if time_diff > Config.VIDEO_TIMEOUT:
        from handlers.video import handle_video_timeout
        await handle_video_timeout(transfer_msg_id, user_id, scheduled_msg_id, time_diff)
        return True
    return False 

async def cleanup_and_process_next(entity_id: int, is_channel: bool = False):
    """Decrement active videos, remove from active set if needed, and process next from queue."""
    decrement_active_videos(entity_id, is_channel=is_channel)
    if not is_channel:
        # Remove user from active if no more active videos
        # Import here to avoid circular import
        from handlers.video.private import remove_user_from_active_if_no_videos
        remove_user_from_active_if_no_videos(entity_id)
    # Always process next from queue
    await process_next_from_queue(entity_id, is_channel=is_channel) 