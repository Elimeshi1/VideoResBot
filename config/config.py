import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

class Config:
    """Configuration class to store all constant values"""
    # --- Credentials ---
    API_ID = int(os.environ.get('API_ID'))
    API_HASH = os.environ.get('API_HASH')
    BOT_TOKEN = os.environ.get('BOT_TOKEN')

    # --- Channels & IDs ---
    ADMIN_ID = int(os.environ.get('ADMIN_ID'))
    TRANSFER_CHANNEL = int(os.environ.get('TRANSFER_CHANNEL'))      # Temporary channel BOT forwards videos TO before processing
    DESTINATION_CHANNEL = int(os.environ.get('DESTINATION_CHANNEL')) # Channel USERBOT schedules videos TO for TG processing
    JUNK_CHANNEL = int(os.environ.get('JUNK_CHANNEL'))          # Channel USERBOT copies messages TO for polling status
    
    # --- Video Processing ---
    MAX_VIDEO_SIZE_GB = 1.5      # Maximum allowed video size in GB
    VIDEO_TIMEOUT = 3600         # Timeout in seconds for video processing (1 hour)
    MAX_QUEUED_VIDEOS = 100      # Max videos waiting in the internal queue 
    MAX_CONCURRENT_VIDEOS_REGULAR = 1  # Max videos a regular user can process at the same time
    MAX_CONCURRENT_VIDEOS_PREMIUM = 5  # Max videos a premium user can process at the same time
    MAX_CONCURRENT_VIDEOS_CHANNEL = 5  # Max videos a channel can process at the same time
    QUEUE_SIZE_LIMIT = 1000      # Maximum number of videos that can be in all queues combined
    CHECK_INTERVAL = 30          # Seconds between polling video status via JUNK_CHANNEL
    K = 0.033                    # Constant for video processing time estimation (adjust based on testing)
    ALLOWED_FORMATS = [          # Allowed video codec/format combinations
        ("h264", "mkv"),
        ("h264", "mp4"),
        ("hevc", "mkv"),
        ("hevc", "mp4"),
        ("h265", "mkv"),
        ("h265", "mp4")
    ]

    # --- Intervals ---
    DB_CLEANUP_INTERVAL_SECONDS = 86400 # Interval for cleaning up expired DB entries (24 hours)

    # --- Payment/Premium --- (Prices in Stars)
    # Plan structure: (plan_id, name, channels, monthly_price)
    PLANS = [
        (1, "Premium Basic", 1, 100),
        (2, "Premium+", 3, 200),
        (3, "Premium Pro", 5, 300),
    ]


    # --- Database ---
    DATABASE_URL = "data/premium_users.db"
    
    # --- Bot Links ---
    BOT_ADMIN_LINK = "http://t.me/VideoResBot?startchannel&admin=post_messages+edit_messages"

    @classmethod
    def max_video_size_bytes(cls) -> int:
        """Get maximum video size in bytes"""
        return int(cls.MAX_VIDEO_SIZE_GB * 1024 * 1024 * 1024) 