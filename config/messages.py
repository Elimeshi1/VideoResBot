"""Stores all user-facing messages and dynamic text generation functions.

This module centralizes all text shown to the user, including static messages,
error messages, button labels, and functions to generate dynamic content based on user data.
"""

from .config import Config

# =============================================================================
# MAIN BOT MESSAGES
# =============================================================================

START_TEXT = (
    f"👋 Welcome to **VidRes Bot**!\n\n"
    f"I process videos and return them in all available qualities.\n\n"
    f"🔧 **First Time Setup:**\n"
    f"• Use /setchannel to configure your output channel\n"
    f"📱 **Other Commands:**\n"
    f"• /premium - Get Premium features\n"
    f"• /help - See all available commands"
)

HELP_TEXT = (
    "🤖 **What does this bot do?**\n"
    "This bot processes your video and sends it back in all available qualities.\n\n"
    "📋 **Allowed Formats:**\n"
    "• MP4/MKV (H264, H265)\n\n"
    "📏 **Maximum Video Size:**\n"
    f"• Up to {Config.MAX_VIDEO_SIZE_GB} GB\n\n"
    "✅ **Usage Limits:**\n"
    "• No daily limits\n"
    "• Free to use (in private chat)\n"
    "• Limited to 1 video simultaneously\n\n"
    "✨ **Premium Features:**\n"
    "• Automatic video processing in channels\n"
    "• Up to 5 videos simultaneously\n\n"
    "🔍 **Available Commands:**\n"
    "• /start - Start a conversation with the bot\n"
    "• /help - Display this message\n"
    "• /setchannel - Set up your output channel (required)\n"
    "• /cancel - Cancel current video processing\n"
    "• /premium - Information about premium membership and manage channels\n\n"
)

OTHER_MESSAGE_PROMPT = (
    "Please send me a video to process. The bot accepts only video messages, "
    "not files or other media types.\n\nFor available commands, type /help"
)

# =============================================================================
# CHANNEL SETUP MESSAGES
# =============================================================================

CHANNEL_SETUP_REQUIRED = (
    "📺 **Channel Setup Required**\n\n"
    "Before processing videos, you need to set up a channel where I'll send the results.\n\n"
    "Use /setchannel to configure your channel."
)

CHANNEL_SETUP_INSTRUCTIONS = (
    "🔧 **Channel Setup Required**\n\n"
    "To use this bot, you need to set up a channel where I'll send your processed videos.\n\n"
    "**Steps:**\n"
    "1. Create a channel or use an existing one\n"
    "2. Add me (@VideoResBot) as an admin with permission to post messages\n"
    "3. Click the button below to select your channel\n\n"
    "**Need help?** [Click here to add me as admin]({bot_admin_link})\n\n"
)

CHANNEL_SETUP_SUCCESS = (
    "✅ **Channel setup successful!**\n\n"
    "Your channel has been configured. All processed videos will now be sent there.\n\n"
    "You can now send me videos for processing! 🎥"
)

CHANNEL_SETUP_FAILED = (
    "❌ **Setup Failed**\n\n"
    "I couldn't send messages to this channel. Please:\n\n"
    "1. Make sure I'm added as an admin\n"
    "2. Give me permission to post messages\n"
    "3. Try the setup again\n\n"
    "[Click here for help]({bot_admin_link})"
)

CHANNEL_SETUP_ERROR = (
    "❌ Failed to save channel configuration. Please try again."
)

CHANNEL_SETUP_GENERAL_ERROR = (
    "❌ An error occurred during channel setup. Please try again."
)

CHANNEL_SETUP_COMPLETE_MESSAGE = (
    "✅ **Channel Setup Complete!**\n\n"
    "This channel is now configured to receive your processed videos from @VideoResBot.\n\n"
    "You can now send videos to the bot for processing!"
)

# =============================================================================
# VIDEO PROCESSING MESSAGES
# =============================================================================

VIDEO_RECEIVED = "Video received! Starting initial checks..."

SYSTEM_BUSY = "The system is currently busy processing other videos. Please try again later."

VIDEO_TOO_LARGE = lambda max_gb: f"Your video is too large.\nPlease send videos smaller than {max_gb} GB."

CHECKING_FORMAT = "Checking video format and codec..."

UNSUPPORTED_CODEC = "Your video uses an unsupported codec-format combination."

QUEUE_LIMIT_REACHED = lambda queued_position, is_premium, max_premium: (
    f"You are already processing the maximum number of videos allowed. "
    f"Your video has been added to the queue (position: {queued_position}).\n\n"
    f"{'Premium users can process up to ' + str(max_premium) + ' videos simultaneously.' if is_premium else 'Each video will be processed when the previous one completes.'}"
)

FAILED_INITIATE_PROCESS = "Failed to initiate video processing. Please try again."

FAILED_SCHEDULE_PROCESS = "Failed to schedule video processing. Please try again."

PROCESSING_VIDEO = lambda estimated_time: (
    f"🎬 Processing your video...\n\n"
    f"⏱️ Estimated processing time: {estimated_time} minutes\n\n"
    f"ℹ️ You will receive the videos once processing is complete.\n"
    f"❌ Use /cancel if you want to cancel the processing."
)

INTERNAL_PROCESS_ERROR = "An internal error occurred while processing your video. Please try again."

CRITICAL_PROCESS_ERROR = (
    "Sorry, a critical error occurred while processing your video. "
    "Please contact support if the issue persists."
)

# =============================================================================
# CANCELLATION MESSAGES
# =============================================================================

CANCEL_NO_ACTIVE_VIDEO = "You don't have any video currently being processed."

CANCEL_SUCCESS = "✅ Video processing cancelled successfully."

CANCEL_STILL_ACTIVE = lambda remaining_count: (
    f"{CANCEL_SUCCESS}\nYou still have {remaining_count} active video(s) in processing. "
    f"Use /cancel again to cancel the next video."
)

ERROR_CANCEL = "An error occurred while trying to cancel the video processing."

# =============================================================================
# PREMIUM PLANS & SUBSCRIPTION
# =============================================================================

PLANS_TEXT_MENU = (
    f"🌟 **PREMIUM PLANS** 🌟\n\n"
    f"Select a plan that fits your needs:\n\n"
    f"💠 **Premium Basic**\n"
    f"• 1 channel\n"
    f"• process 5 videos simultaneously\n\n"
    f"💠 **Premium+**\n"
    f"• 3 channels\n"
    f"• process 5 videos simultaneously\n\n"
    f"💠 **Premium Pro**\n"
    f"• 5 channels\n"
    f"• process 5 videos simultaneously\n\n"
    f"Select a plan to purchase:"
)

PLANS_TEXT_COMMAND = (
    f"🌟 **PREMIUM PLANS** 🌟\n\n"
    f"Select a plan that fits your needs:\n\n"
    f"💠 **Premium Basic**\n"
    f"• 1 channel\n"
    f"• process 5 videos simultaneously\n"
    f"💠 **Premium+**\n"
    f"• 3 channels\n"
    f"• process 5 videos simultaneously\n"
    f"💠 **Premium Pro**\n"
    f"• 5 channels\n"
    f"• process 5 videos simultaneously\n"
    f"Select a plan to purchase:"
)

def premium_status_text(expiry_date: str, plan_name: str, num_channels: int, 
                       max_channels: int, active_channels: int, days_remaining: str | int) -> str:
    """Returns the formatted premium status message."""
    return (
        f"✨ **PREMIUM STATUS** ✨\n\n"
        f"• Status: ✅ Active until {expiry_date}\n"
        f"• Plan: {plan_name}\n"
        f"• Channels: {num_channels}/{max_channels}\n"
        f"• Days remaining: {days_remaining}\n\n"
        f"Use the buttons below to manage your channels:"
    )

def duration_selection_text(plan_name: str, channels: int, monthly_price: int) -> str:
    """Returns the formatted duration selection message."""
    return (
        f"🕒 **SELECT SUBSCRIPTION PERIOD** 🕒\n\n"
        f"Selected plan: **{plan_name}** ({channels} {'channel' if channels == 1 else 'channels'})\n"
        f"Base price: {monthly_price} ⭐ per month\n\n"
        f"Choose your subscription period:"
    )

# =============================================================================
# PAYMENT & PURCHASE MESSAGES
# =============================================================================

def invoice_title(plan_name: str, months: int) -> str:
    """Generates the title for the purchase invoice."""
    return f"{plan_name} - {months} Month{'s' if months > 1 else ''}"

def invoice_description(channels: int, months: int) -> str:
    """Generates the description for the purchase invoice."""
    duration_desc = f"{months} month{'s' if months > 1 else ''}"
    channel_desc = f"{channels} channel{'s' if channels > 1 else ''}"
    return f"Premium subscription for {duration_desc}, including {channel_desc}."

def successful_payment_text(expiry_date_str: str) -> str:
    """Returns successful payment confirmation message."""
    return (
        f"✅ **Payment Successful!** 🎉\n\n"
        f"Your premium subscription is now active until {expiry_date_str}.\n\n"
        f"Use the /premium command to manage your channels.\n\n"
        f"Enjoy the benefits! ✨"
    )

# =============================================================================
# UPGRADE MESSAGES
# =============================================================================

def upgrade_options_text(current_plan: str, current_channels: int, current_expiry: str) -> str:
    """Returns upgrade options message."""
    return (
        f"⭐ **UPGRADE YOUR PLAN** ⭐\n\n"
        f"Current Plan: **{current_plan}** ({current_channels} channels)\n"
        f"Expires: {current_expiry}\n\n"
        f"Select a new plan to upgrade to:"
    )

def upgrade_duration_text(new_plan: str, new_channels: int, upgrade_cost: int) -> str:
    """Returns upgrade confirmation message."""
    return (
        f"🔄 **CONFIRM UPGRADE** 🔄\n\n"
        f"Upgrading to: **{new_plan}** ({new_channels} channels)\n"
        f"Additional cost: {upgrade_cost} ⭐\n\n"
        f"Your subscription expiry date will remain the same.\n"
        f"Confirm your upgrade:"
    )

def upgrade_successful_text(new_plan: str, new_channels: int) -> str:
    """Returns successful upgrade message."""
    return (
        f"✅ **Upgrade Successful!** 🎉\n\n"
        f"You are now on the **{new_plan}** plan with {new_channels} channels.\n"
        f"Your expiry date remains the same."
    )

# =============================================================================
# CHANNEL MANAGEMENT MESSAGES
# =============================================================================

def channel_limit_reached_text(current_channels: int, max_channels: int) -> str:
    """Returns channel limit reached message."""
    return (
        f"⚠️ **CHANNEL LIMIT REACHED** ⚠️\n\n"
        f"You have {current_channels} channels and your plan allows {max_channels}.\n"
        f"To add more channels, you need to upgrade your subscription."
    )

def add_channel_prompt_text(current_channels: int, max_channels: int) -> str:
    """Returns add channel prompt message."""
    return (
        f"👇 **ADD CHANNEL TO BOT** 👇\n\n"
        f"Press '{BUTTON_SELECT_CHANNEL}' and choose a channel from the list.\n\n"
        f"The bot will need admin permissions to process videos in the channel.\n"
        f"You have {current_channels}/{max_channels} channels used.\n\n"
        f"Use the button below to select a channel:"
    )

def channel_already_added_text(channel_id: int, status: str, expiry_str: str, days_left: int) -> str:
    """Returns channel already added message."""
    return (
        f"ℹ️ **CHANNEL ALREADY ADDED** ℹ️\n\n"
        f"• Channel ID: `{channel_id}`\n"
        f"• Status: {status}\n"
        f"• Expires: {expiry_str}\n"
        f"• Days left: {days_left}"
    )

def channel_limit_reached_on_select_text(current_channels: int, max_channels: int) -> str:
    """Returns channel limit reached on selection message."""
    return (
        f"⚠️ **CHANNEL LIMIT REACHED** ⚠️\n\n"
        f"Your subscription allows {max_channels} channels and you already have {current_channels}.\n"
        f"To add more channels, please upgrade your subscription via the /premium command."
    )

def channel_added_success_text(channel_id: int, current_channels: int, max_channels: int) -> str:
    """Returns channel added success message."""
    return (
        f"✅ **CHANNEL ADDED** ✅\n\n"
        f"• Channel ID: `{channel_id}`\n"
        f"• Channels used: {current_channels + 1}/{max_channels}\n"
        f"• Expires with your premium subscription\n\n"
        f"__**Make sure the bot is an admin in your channel**__"
    )

NO_CHANNELS_TEXT = (
    f"📺 **YOUR CHANNELS** 📺\n\n"
    f"You don't have any channels yet.\n"
    f"Use the button below to add your first channel."
)

def view_channels_text(active_channels: int, total_channels: int) -> str:
    """Returns view channels message."""
    return (
        f"📺 **YOUR CHANNELS ({active_channels}/{total_channels} ACTIVE)** 📺\n\n"
        f"Select a channel to view details or remove it:"
    )

def channel_details_text(channel_id: int, status: str, expiry_str: str, days_left: int) -> str:
    """Returns channel details message."""
    return (
        f"ℹ️ **CHANNEL DETAILS** ℹ️\n\n"
        f"• Channel ID: `{channel_id}`\n"
        f"• Status: {status}\n"
        f"• Expires: {expiry_str}\n"
        f"• Days left: {days_left}\n\n"
        f"You can remove this channel using the button below:"
    )

def confirm_remove_channel_text(channel_id: int) -> str:
    """Returns confirm channel removal message."""
    return (
        f"🗑️ **CONFIRM REMOVAL** 🗑️\n\n"
        f"Are you sure you want to remove channel `{channel_id}`?\n\n"
        f"This action cannot be undone."
    )

def channel_removed_success_text(channel_id: int) -> str:
    """Returns channel removed success message."""
    return f"✅ Channel `{channel_id}` has been successfully removed."

def remove_channel_command_success_text(channel_id: int) -> str:
    """Returns command-based channel removal success message."""
    return f"✅ Channel `{channel_id}` removed successfully."

# =============================================================================
# BUTTON LABELS
# =============================================================================

BUTTON_ADD_CHANNEL = "➕ Add Channel"
BUTTON_MY_CHANNELS = "📋 My Channels"
BUTTON_UPGRADE_PLAN = "⭐ Upgrade Plan"
BUTTON_BACK_TO_PLANS = "↩️ Back to Plans"
BUTTON_BACK_TO_MENU = "↩️ Back to Menu"
BUTTON_CONFIRM_UPGRADE = "✅ Confirm Upgrade"
BUTTON_SELECT_CHANNEL = "📺 Select a Channel"
BUTTON_CANCEL = "❌ Cancel"
BUTTON_REMOVE_CHANNEL = "🗑️ Remove Channel"
BUTTON_CONFIRM_REMOVE = "✅ Yes, Remove"
BUTTON_BACK_TO_CHANNELS = "↩️ Back to Channels"

# =============================================================================
# ERROR MESSAGES
# =============================================================================

# General Errors
ERROR_GENERIC = "An error occurred. Please try again later."
ERROR_PREMIUM_DATA = "Failed to retrieve premium data."
ERROR_CALCULATING_DAYS = "Failed to calculate remaining days."

# Plan & Purchase Errors
ERROR_PLAN_SELECTION = "An error occurred during plan selection."
ERROR_PURCHASE = "An error occurred during the purchase process."
ERROR_UPGRADE = "An error occurred during the upgrade process."
ERROR_ALREADY_MAX_PLAN = "You are already on the highest plan."
ERROR_PAYMENT_FAILED = "Payment failed or was cancelled."

# Permission Errors
ERROR_NOT_PREMIUM = "Only premium users can perform this action."
ERROR_COMMAND_PREMIUM_ONLY = "This command is only available for premium users."

# Channel Management Errors
ERROR_CHANNEL_LIMIT_REACHED = "Channel limit reached. Please upgrade your plan."
ERROR_RETRIEVING_CHANNEL_ID = "Error retrieving channel ID."
ERROR_ADDING_CHANNEL = "Failed to add channel."
ERROR_PROCESSING_CHANNEL = "An error occurred while processing your channel."
ERROR_VIEWING_CHANNELS = "An error occurred while retrieving your channels."
ERROR_CHANNEL_NOT_FOUND = "Channel not found."
ERROR_REMOVING_CHANNEL = "Failed to remove channel."

# Command Errors
ERROR_COMMAND_CHANNEL_ID_MISSING = "Please provide the Channel ID to remove."
ERROR_COMMAND_CHANNEL_NOT_FOUND = "Channel not found for removal."
ERROR_COMMAND_CHANNEL_REMOVAL_FAILED = "Failed to remove the channel via command."

# =============================================================================
# BAN MESSAGES
# =============================================================================

USER_BANNED = lambda reason: f"🚫 **You are banned from using this bot.**\n\n**Reason:** {reason}\n\nContact support if you believe this is an error."

BAN_SUCCESS = lambda user_id, reason: f"✅ User {user_id} has been banned.\n**Reason:** {reason}"
UNBAN_SUCCESS = lambda user_id: f"✅ User {user_id} has been unbanned."
BAN_USAGE = "Usage: /ban user_id reason"
UNBAN_USAGE = "Usage: /unban user_id"
BAN_ERROR = "An error occurred while processing the ban command."
UNBAN_ERROR = "An error occurred while processing the unban command."
USER_NOT_FOUND = lambda user_id: f"User {user_id} not found in database."

# =============================================================================
# ADMIN MESSAGES
# =============================================================================

ADMIN_ONLY_COMMAND = "This command is only available to admins."
REFUND_USAGE = "Usage: /refund user_id payment_charge_id"
REFUND_SUCCESS = lambda user_id: f"✅ Successfully initiated refund for user {user_id}"
REFUND_FAILED = lambda error: f"❌ Failed to process refund: {error}"
REFUND_ERROR = "An error occurred while processing the refund command." 