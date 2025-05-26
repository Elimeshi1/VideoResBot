import os
import asyncio
from asyncio.subprocess import PIPE
from config.config import Config
from utils.logger import logger
from pyrogram.types import Message
from config.state import State
from pyrogram import errors

async def run_cmd(*args, **kwargs):
    """Run a command asynchronously and return the process"""
    return await asyncio.create_subprocess_exec(*args, **kwargs)

async def get_video_info(bot, media, limit=5):
    """
    Get the codec and format of a video by downloading both beginning and end parts of it and using ffprobe
    
    Args:
        bot: The Pyrogram client
        media: The media object
        limit: Number of chunks to download from beginning and end (default: 5)
        
    Returns:
        tuple: (codec, format) or (None, None) if not found
    """
    if not media or not media.file_name:
        return None, None
    
    # Get the file extension for format detection
    file_ext = os.path.splitext(media.file_name)[1].lower().lstrip('.')
    
    des_path = os.path.join(os.getcwd(), media.file_name)
    
    try:
        # Open file in binary append mode
        with open(des_path, "wb") as f:
            # Get first chunks of the file
            logger.info(f"[🔍] Downloading first {limit} chunks of the file")
            chunk_count = 0
            async for chunk in bot.stream_media(media, limit=limit):
                # Write the chunk synchronously
                f.write(chunk)
                chunk_count += 1
            
            # Get last chunks of the file
            logger.info(f"[🔍] Downloading last {limit} chunks of the file")
            async for chunk in bot.stream_media(media, offset=-limit):
                # Write the chunk synchronously
                f.write(chunk)
        
        # Run ffprobe to get codec
        process = await run_cmd("ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=codec_name", "-of", "default=nw=1", des_path, stdout=PIPE)
        stdout, _ = await process.communicate()
        codec = stdout.decode().strip().replace("codec_name=", "").lower()
        
        return codec, file_ext
    except Exception as e:
        logger.error(f"Error in get_video_info: {e}")
        return None, None
    finally:
        # Clean up file after use
        try:
            if os.path.exists(des_path):
                os.remove(des_path)
        except Exception as e:
            logger.error(f"Error removing temporary file: {e}")

def calculate_processing_time(duration: int, height: int) -> int:
    """
    Calculate estimated processing time in minutes based on video duration and height
    
    Args:
        duration: Video duration in seconds
        height: Video height in pixels
        
    Returns:
        int: Estimated processing time in minutes (rounded up)
    """
    # Calculate number of qualities based on video height
    if height >= 1080:
        num_qualities = 4  # Original + 1080p, 720p, 480p
    elif height >= 720:
        num_qualities = 3  # Original + 720p, 480p
    else:
        num_qualities = 2  # Original + 480p
        
    # Convert duration to minutes
    duration_minutes = duration / 60
    
    # Calculate processing time in minutes
    # Formula: 0.033 × (Duration in minutes × Number of qualities)
    processing_time = Config.K * (duration_minutes * num_qualities)
    
    # Round up to nearest integer
    return int(processing_time + 0.99)


async def check_video_size(video, source_info="") -> bool:
    """Check if video size is within allowed limits"""
    if not hasattr(video, 'file_size') or not video.file_size:
        logger.warning(f"[⚠️] Video object missing file_size attribute {source_info}")
        return True # Allow processing if size unknown

    if video.file_size > Config.max_video_size_bytes():
        return False
    return True

async def check_video_codec_format(video, source_info="") -> bool:
    """Check if video codec and format are supported using get_video_info"""
    try:
        # Use the existing get_video_info function from this module
        codec, video_format = await get_video_info(State.bot, video)
        
        if codec and video_format:
            logger.info(f"[🎬] Detected codec: {codec}, format: {video_format} {source_info}")
            
            codec = codec.lower()
            video_format = video_format.lower()
            
            # Check against allowed formats defined in Config
            if (codec, video_format) not in Config.ALLOWED_FORMATS:
                logger.info(f"[❌] Unsupported codec-format combination: {codec}-{video_format} {source_info}")
                return False
            logger.info(f"[✅] Supported codec-format combination: {codec}-{video_format} {source_info}")
            return True
        else:
            # If detection failed, log warning but allow processing
            logger.warning(f"[⚠️] Could not detect codec/format {source_info}. Allowing processing.")
            return True 
    except Exception as e:
        logger.error(f"[⚠️] Error detecting codec/format {source_info}: {e}. Allowing processing.")
        return True # Allow processing on error

async def find_and_clean_tracking_info(transfer_msg_id=None, channel_id=None, message_id=None) -> bool:
    """Find and clean up video tracking information from State based on available IDs."""
    found_and_cleaned = False
    try:
        target_transfer_id = None
        user_id_to_clean = None

        # If transfer_msg_id is provided, use it directly
        if transfer_msg_id is not None:
            if transfer_msg_id in State.video_info:
                target_transfer_id = transfer_msg_id
                user_id_to_clean = State.video_info[transfer_msg_id][0]
                logger.info(f"[🧹] Found tracking info via Transfer ID: {transfer_msg_id}")
        
        # If channel info is provided and not found yet, search by channel and message ID
        elif channel_id is not None and message_id is not None:
            for transfer_id, data in list(State.user_videos.items()):
                # Check if it's the tuple format with channel data
                if isinstance(data, tuple) and len(data) == 2:
                    stored_channel_id, stored_message_id = data
                    if stored_channel_id == channel_id and stored_message_id == message_id:
                        if transfer_id in State.video_info:
                            target_transfer_id = transfer_id
                            user_id_to_clean = State.video_info[transfer_id][0]
                            logger.info(f"[🧹] Found tracking info via Channel/Message ID: {channel_id}/{message_id}")
                            break # Found it

        # If found, perform cleanup
        if target_transfer_id is not None and user_id_to_clean is not None:
            from utils.cleanup import clean_up_tracking_info
            clean_up_tracking_info(target_transfer_id, user_id_to_clean)
            logger.info(f"[🧹] Cleaned up tracking info for Transfer ID: {target_transfer_id}")
            found_and_cleaned = True
        else:
             logger.warning(f"[⚠️] Tracking info not found for cleanup. Provided IDs: transfer={transfer_msg_id}, channel={channel_id}, msg={message_id}")

    except Exception as e:
        logger.error(f"[❌] Error in find_and_clean_tracking_info: {e}")
    
    return found_and_cleaned

def format_video_info(original_size: int, duration: int, processing_time: float, estimated_time: float, sent_qualities: int) -> str:
    """Format video information for the status message."""
    try:
        # Ensure all numeric variables have the correct type or handle errors
        duration_min = int(duration // 60) if duration else 0
        duration_sec = int(duration % 60) if duration else 0
        size_mb = float(original_size / (1024*1024)) if original_size else 0.0
        proc_time_min = float(processing_time) if processing_time is not None else 0.0
        est_time_min = float(estimated_time) if estimated_time is not None else 0.0
        qual_sent = int(sent_qualities) if sent_qualities is not None else 0
        
        return (
            f"🎬 **Original Size:** {size_mb:.2f} MB\n"
            f"⏱️ **Duration:** {duration_min}:{duration_sec:02d}\n"
            f"⚙️ **Processing Time:** {proc_time_min:.2f} minutes\n"
            f"🔄 **Estimated Time:** {est_time_min:.1f} minutes\n"
            f"🎞️ **Qualities Sent:** {qual_sent}"
        )
    except Exception as e:
         logger.error(f"[❌] Error formatting video info: {e}")
         return "Error formatting video details."

async def is_userbot_connected(app):
    """Returns True if the userbot session is valid and connected, False otherwise."""
    try:
        await app.get_me()
    except (
        errors.ActiveUserRequired,
        errors.AuthKeyInvalid,
        errors.AuthKeyPermEmpty,
        errors.AuthKeyUnregistered,
        errors.AuthKeyDuplicated,
        errors.SessionExpired,
        errors.SessionPasswordNeeded,
        errors.SessionRevoked,
        errors.UserDeactivated,
        errors.UserDeactivatedBan,
    ):
        return False
    else:
        return True
