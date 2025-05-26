from datetime import datetime
from typing import Dict, Set, Tuple, Optional, Union
from pyrogram import Client
from utils.queue_manager import (
    user_video_queue,
    channel_video_queue,
    active_videos_count_users,
    active_videos_count_channels
)

class State:
    """Class to manage the application state"""
    # Dictionary to store video information: {transfer_msg_id: (user_id, scheduled_msg_id, timestamp, original_size, duration)}
    video_info: Dict[int, Tuple[int, int, datetime, int, int]] = {}

    # Set to keep track of users with active videos
    active_users: Set[int] = set()

    # Dictionary to track which transfer_msg_id belongs to which user
    user_videos: Dict[int, Union[int, Tuple[int, int]]] = {}

    # Global event loop
    main_event_loop = None

    # Client instances
    bot: Optional[Client] = None
    userbot: Optional[Client] = None

    # Map scheduled_message_id (from destination channel) to transfer_message_id
    scheduled_to_transfer_map: Dict[int, int] = {}

    # Dictionary to store pending upgrade payloads keyed by a unique ID
    pending_upgrades: Dict[str, str] = {}
    
    # References to queues and counters from queue_manager
    user_video_queue = user_video_queue
    channel_video_queue = channel_video_queue
    active_videos_count_users = active_videos_count_users
    active_videos_count_channels = active_videos_count_channels

    @classmethod
    def initialize(cls, bot_instance, userbot_instance):
        """Initialize the client instances in the State class."""
        cls.bot = bot_instance
        cls.userbot = userbot_instance 