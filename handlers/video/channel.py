"""
Channel video handler module.

This module handles videos posted in channels where the bot is a member.
"""

from pyrogram import Client
from pyrogram.types import Message
from utils.logger import logger
from config.state import State
from config.config import Config
from utils.db import db
from utils.video_utils import (
    check_video_size,
    check_video_codec_format
)
from utils.video_processor import (
    schedule_video_to_destination,
    track_video_progress,
    forward_to_transfer_channel
)
from utils.queue_manager import (
    increment_active_videos,
    decrement_active_videos,
    get_active_videos_count,
    add_to_queue
)

async def channel_video_handler(client: Client, message: Message) -> None:
    """Handles videos posted in channels where the bot is a member"""
    try:
        # Skip if no video
        if not message.video:
            return
            
        channel_id = message.chat.id
        channel_name = message.chat.title
        
        logger.info(f"[📺] Received video from channel {channel_id} ({channel_name})")
        
        # Check if the channel is activated by a premium user
        if not db.is_channel_active(channel_id):
            logger.info(f"[⚠️] Channel {channel_id} is not activated by a premium user. Skipping.")
            return
        
        # Check if queue is full
        if len(State.video_info) >= Config.MAX_QUEUED_VIDEOS:
            logger.info(f"[⚠️] Video queue is full. Current size: {len(State.video_info)}")
            return
            
        # Call the main processing function
        await process_channel_video(message)
        
    except Exception as e:
        logger.error(f"[❌] Error processing video from channel {message.chat.id if message and message.chat else 'unknown'}: {e}", exc_info=True)

async def process_channel_video(message: Message) -> None:
    """Main function to process a channel video, with queue management"""
    try:
        channel_id = message.chat.id
        channel_name = message.chat.title

        if message.video and message.video.alternative_videos:
            logger.info(f"[⚡️] Video from channel {channel_id} ({channel_name}) was already processed by Telegram (found alternative_videos). Skipping.")
            return
        
        # Check video size
        if not await check_video_size(message.video, f"from channel {channel_id} ({channel_name})"):
            logger.info(f"[❌] Video from channel {channel_id} ({channel_name}) is too large. Skipping.")
            return
        
        # Check video codec and format
        if not await check_video_codec_format(message.video, f"from channel {channel_id} ({channel_name})"):
            return
        
        # Check if channel is at its active videos limit
        active_count = get_active_videos_count(channel_id, is_channel=True)
        
        if active_count >= Config.MAX_CONCURRENT_VIDEOS_CHANNEL:
            # Add to queue instead of processing immediately
            logger.info(f"[⏳] Channel {channel_id} ({channel_name}) at concurrent limit. Queuing video {message.id}.")
            add_to_queue(message, channel_id, is_channel=True)
            return
        
        # If all checks passed, mark as active and increment counter
        increment_active_videos(channel_id, is_channel=True)
        
        # Forward to transfer channel
        transfer_msg = await forward_to_transfer_channel(message)
        if not transfer_msg:
            logger.error(f"[❌] Failed to forward video from channel {channel_id}")
            # Decrement since we failed
            decrement_active_videos(channel_id, is_channel=True)
            return 
        transfer_msg_id = transfer_msg.id
            
        # Schedule to destination channel
        scheduled_msg_id = await schedule_video_to_destination(transfer_msg_id)
        if not scheduled_msg_id:
            logger.error(f"[❌] Failed to schedule video from channel {channel_id} (Transfer ID: {transfer_msg_id})")
            # Decrement since we failed
            decrement_active_videos(channel_id, is_channel=True)
            return
            
        # Track progress with channel data
        await track_video_progress(
            transfer_msg_id,
            -1,  # Special user_id for channel videos
            scheduled_msg_id,
            message.video.file_size,
            message.video.duration,
            (channel_id, message.id)  # Store channel ID and message ID as tuple
        )
        
        logger.info(f"[✅] Channel video {message.id} from {channel_id} forwarded and scheduled. Transfer ID: {transfer_msg_id}, Scheduled ID: {scheduled_msg_id}")
    
    except Exception as e:
        logger.error(f"[❌] Error processing channel video: {e}")
        # Handle error and decrement counter
        decrement_active_videos(channel_id, is_channel=True)
