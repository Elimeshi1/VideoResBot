"""
Video handlers package for the Telegram Video Quality Bot.

This package provides handlers for initiating video processing:
- private.py: Handlers for videos in private chats
- channel.py: Handlers for videos and edits in channels
"""

from pyrogram import Client, filters
from pyrogram.handlers import MessageHandler
from config.config import Config

from .private import process_video_handler
from .channel import channel_video_handler

# Define what handlers are publicly exported from this package
__all__ = [
    "process_video_handler",         # Handles new videos in private chats
    "channel_video_handler",         # Handles new videos in channels
]

def register_video_handlers(client: Client):
    """Registers all video-related handlers"""
    # 1. Private video handler
    client.add_handler(
        MessageHandler(
            process_video_handler,
            filters=filters.private & filters.video
        ),
        group=3
    )

    # 2. Channel video handler (for new posts in subscribed channels)
    client.add_handler(
        MessageHandler(
            channel_video_handler,
            filters=filters.channel & filters.video & ~filters.chat(Config.DESTINATION_CHANNEL) # Exclude destination channel
        ),
        group=3
    )
