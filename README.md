# Telegram Video Quality Bot

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Telegram Bot API](https://img.shields.io/badge/Telegram%20Bot%20API-Latest-blue.svg)](https://core.telegram.org/bots/api)

A sophisticated Telegram bot that leverages Telegram's native video processing capabilities to enhance video quality for channels under 10K subscribers.

## 🤖 Try the Bot

You can find and interact with the bot at: **[@VideoResBot](https://t.me/videoresbot)**

Simply send a video file to get started with automatic quality enhancement!


## 🎯 Overview

Telegram has a built-in feature that processes videos into multiple quality levels, but this feature is only available for channels with 10K+ subscribers. This bot provides a workaround by:

1. **Receiving videos** from users via the bot
2. **Transferring** videos to a processing channel via an intermediate channel
3. **Scheduling** videos in a 10K+ subscriber channel using a userbot
4. **Monitoring** the processing status and detecting when Telegram completes quality enhancement
5. **Delivering** the processed video with multiple quality options back to the user
6. **Cleaning up** scheduled messages to maintain efficiency

## ✨ Features

### Core Functionality
- **Automatic Video Processing**: Converts videos to multiple quality levels using Telegram's native processing
- **Queue Management**: Handles video processing queue with configurable limits (up to 100 scheduled messages)
- **Real-time Monitoring**: Background tasks continuously check processing status
- **Smart Cleanup**: Automatic removal of processed videos from scheduled messages

### Premium Features (Paid via Telegram Stars)
- **Channel Integration**: Premium users can add the bot to their own channels for direct processing
- **Increased Concurrency**: Up to 5 simultaneous video processing slots (vs 1 for regular users)
- **Multiple Plans Available**:
  - Premium Basic (1 channel, 200 Stars/month)
  - Premium+ (3 channels, 300 Stars/month)  
  - Premium Pro (5 channels, 400 Stars/month)

### Technical Features
- **Dual Client Architecture**: Bot client for user interaction + Userbot for channel operations
- **Comprehensive Logging**: Detailed logging system for monitoring and debugging
- **Database Management**: SQLite database with automatic cleanup of expired subscriptions
- **Error Handling**: Robust error handling with graceful shutdown capabilities
- **Video Format Support**: Supports h264/h265/hevc codecs in mp4/mkv containers


## 📋 Requirements

- Python 3.8+
- Telegram API credentials (API ID, API Hash)
- Bot token from @BotFather
- Userbot session (for channel operations)
- Access to channels:
  - Transfer channel (temporary storage)
  - Destination channel (10K+ subscribers for processing)
  - Junk channel (for status monitoring)

## 🚀 Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/telegram-video-quality-bot.git
   cd telegram-video-quality-bot
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configuration**:
   - Copy `env.example` to `.env`
   - Fill in your Telegram API credentials and channel IDs
   ```bash
   cp env.example .env
   ```

4. **Setup channels**:
   - Create the required channels (transfer, destination 10K+, junk)
   - Add the bot and userbot to appropriate channels
   - Update channel IDs in `.env`

5. **Initialize userbot session**:
   ```bash
   python main.py
   ```
   On first run, you'll be prompted to enter your phone number and connect to Telegram. The session will be saved in the sessions folder.


## ⚙️ Configuration

### Environment Variables

```env
# Telegram API Credentials
API_ID=your_api_id_here
API_HASH=your_api_hash_here
BOT_TOKEN=your_bot_token_here

# Channel IDs
ADMIN_ID=your_admin_id_here
TRANSFER_CHANNEL=your_transfer_channel_id_here
DESTINATION_CHANNEL=your_destination_channel_id_here
JUNK_CHANNEL=your_junk_channel_id_here
```

### Key Settings (config/config.py)

- `MAX_VIDEO_SIZE_GB`: Maximum video file size (default: 1.5GB)
- `VIDEO_TIMEOUT`: Processing timeout (default: 1 hour)
- `MAX_QUEUED_VIDEOS`: Queue limit (default: 100)
- `CHECK_INTERVAL`: Status polling interval (default: 30 seconds)

## 🎮 Usage

1. **Start the bot**:
   ```bash
   python main.py
   ```

2. **For regular users**:
   - Send a video to the bot
   - Wait for processing completion
   - Receive processed video with multiple quality options

3. **For premium users**:
   - Purchase a premium plan using `/premium` command
   - Add bot to your channel(s)
   - Enjoy enhanced processing capabilities


## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ⚠️ Disclaimer

This bot works by utilizing Telegram's native video processing feature through legitimate API calls. Ensure compliance with Telegram's Terms of Service when deploying.

## 🆘 Support

For issues and questions:
- Open an issue on GitHub
- Check the logs for error details
- Ensure all configuration is correct

---

**Note**: This bot requires access to a channel with 10K+ subscribers for the video processing feature to work. The bot manages the entire workflow automatically once properly configured. 
