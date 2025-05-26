"""
Queue and active video tracking module.

This module handles:
- Tracking active videos counts for users and channels
- Managing queues of videos waiting to be processed
"""

from collections import defaultdict, deque
from typing import Dict, Deque, Optional

# Dictionary to store queues for videos waiting to be processed
# For users: {user_id: deque of Message objects}
user_video_queue: Dict[int, Deque] = defaultdict(deque)

# For channels: {channel_id: deque of Message objects}
channel_video_queue: Dict[int, Deque] = defaultdict(deque)

# Track active videos count per entity
active_videos_count_users: Dict[int, int] = defaultdict(int)
active_videos_count_channels: Dict[int, int] = defaultdict(int)

def increment_active_videos(entity_id: int, is_channel: bool = False) -> None:
    """Increment the count of active videos for a user or channel"""
    if is_channel:
        active_videos_count_channels[entity_id] += 1
    else:
        active_videos_count_users[entity_id] += 1
        
def decrement_active_videos(entity_id: int, is_channel: bool = False) -> None:
    """Decrement the count of active videos for a user or channel"""
    if is_channel:
        if active_videos_count_channels[entity_id] > 0:
            active_videos_count_channels[entity_id] -= 1
    else:
        if active_videos_count_users[entity_id] > 0:
            active_videos_count_users[entity_id] -= 1
            
def get_active_videos_count(entity_id: int, is_channel: bool = False) -> int:
    """Get the count of active videos for a user or channel"""
    if is_channel:
        return active_videos_count_channels[entity_id]
    else:
        return active_videos_count_users[entity_id]

def add_to_queue(message, entity_id: int, is_channel: bool = False) -> None:
    """Add a video message to the appropriate queue"""
    if is_channel:
        channel_video_queue[entity_id].append(message)
    else:
        user_video_queue[entity_id].append(message)
        
def get_next_from_queue(entity_id: int, is_channel: bool = False):
    """Get the next video message from the queue if available"""
    queue = channel_video_queue[entity_id] if is_channel else user_video_queue[entity_id]
    if queue:
        return queue.popleft()  # Remove and return the leftmost item
    return None
    
def has_queued_videos(entity_id: int, is_channel: bool = False) -> bool:
    """Check if there are videos in the queue for a user or channel"""
    queue = channel_video_queue[entity_id] if is_channel else user_video_queue[entity_id]
    return len(queue) > 0 