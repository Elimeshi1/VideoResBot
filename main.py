"""
Main module for the Telegram Video Quality Bot.
"""

import asyncio
import signal
from pyrogram import Client, compose
from utils.logger import logger
from utils.cleanup import run_periodic_cleanup_task, cleanup_scheduled_messages
from utils.db import db
from config.state import State
from config.config import Config

# --- Import Handler Registration Functions --- 
from handlers.commands import register_command_handlers
from handlers.payment import register_payment_handlers
from handlers.video import register_video_handlers


def signal_handler(signum, frame) -> None:
    """Handles termination signals (SIGINT, SIGTERM)"""
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    # Request the main event loop to stop
    if State.main_event_loop and State.main_event_loop.is_running():
        State.main_event_loop.stop()
    else:
         logger.warning("Main event loop not found or not running during signal handling.")

async def init_clients() -> list:
    """Initialize the Pyrogram bot and userbot clients"""
    try:
        # Ensure sessions directory exists
        import os
        sessions_dir = "sessions"
        os.makedirs(sessions_dir, exist_ok=True)
        logger.info(f"[📁] Sessions directory ensured at: {os.path.abspath(sessions_dir)}")
        
        # Create bot client
        bot = Client(
             "sessions/quality_bot", 
             api_id=Config.API_ID, 
             api_hash=Config.API_HASH, 
             bot_token=Config.BOT_TOKEN
        )
        
        # Create userbot client
        userbot = Client(
             "sessions/userbot",
             api_id=Config.API_ID, 
             api_hash=Config.API_HASH 
        )
        
        # Initialize the State with the client instances
        State.initialize(bot, userbot)
        logger.info("Clients initialized.")
        
        return [bot, userbot]
    except Exception as e:
        logger.error(f"Fatal error initializing clients: {e}", exc_info=True)
        raise # Re-raise exception to stop the bot if clients can't init

async def register_all_handlers() -> None:
    """Register all message and callback handlers by calling package-specific functions."""
    if not State.bot:
        logger.error("Bot client not initialized. Cannot register handlers.")
        return
    
    # Check if handlers were already registered
    if hasattr(State, '_handlers_registered') and State._handlers_registered:
        logger.warning("[⚠️] Handlers already registered! Skipping duplicate registration.")
        return
        
    logger.info("[🔧] Registering handlers...")
    register_command_handlers(State.bot)
    register_payment_handlers(State.bot)
    register_video_handlers(State.bot)
    
    # Mark handlers as registered
    State._handlers_registered = True
    
    # Log number of registered handlers per group
    for group_id in [1, 2, 3, 4]:
        if group_id in State.bot.dispatcher.groups:
            count = len(State.bot.dispatcher.groups[group_id])
            logger.info(f"[📊] Group {group_id}: {count} handlers registered")
    
    logger.info("[✅] All handlers registered successfully.")

async def cleanup_db() -> None:
    """Periodically clean up expired premium memberships and channel subscriptions"""
    logger.info("Starting periodic database cleanup task...")
    while True:
        try:
            await asyncio.sleep(Config.DB_CLEANUP_INTERVAL_SECONDS) 
            db.cleanup_expired()
            logger.info("[🧹] Periodic database cleanup completed")
        except asyncio.CancelledError:
            logger.info("Database cleanup task cancelled.")
            break
        except Exception as e:
            logger.error(f"[❌] Error during periodic database cleanup: {e}", exc_info=True)
            # Wait longer before retrying after an error
            await asyncio.sleep(3600)

async def main() -> None:
    """Main async function that sets up and runs the bot."""
    # Get the current event loop and store it for the signal handler
    State.main_event_loop = asyncio.get_running_loop()
    
    try:
        # Initialize clients (bot and userbot)
        clients = await init_clients()
        
        # Register handlers on the bot client
        await register_all_handlers()
        
        # Start background tasks
        db_cleanup_task = asyncio.create_task(cleanup_db())
        tracking_cleanup_task = asyncio.create_task(run_periodic_cleanup_task())
        logger.info("Background tasks started.")
        
        # Run both clients using compose
        await compose(clients)
        
        logger.info("Clients stopped, preparing for shutdown...")
        
        # Cancel background tasks upon stopping
        logger.info("Cancelling background tasks...")
        db_cleanup_task.cancel()
        tracking_cleanup_task.cancel()
        await asyncio.gather(db_cleanup_task, tracking_cleanup_task, return_exceptions=True)
        logger.info("Background tasks cancelled.")
    
    except KeyboardInterrupt:
        # Already handled by signal handler, just log
        logger.info("KeyboardInterrupt received.")
    except Exception as e:
        logger.error(f"Critical error in main function: {e}", exc_info=True)
    finally:
        # Graceful shutdown sequence
        logger.info("Starting final cleanup and shutdown...")
        try:
            # Perform any final synchronous cleanup if needed
            await cleanup_scheduled_messages()
        except Exception as final_cleanup_err:
            logger.error(f"Error during final synchronous cleanup: {final_cleanup_err}")
        
        logger.info("[👋] Application shutdown complete.")

if __name__ == "__main__":    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run the main async function
    try:
        asyncio.run(main())
    except Exception as e:
         # Catch top-level errors during asyncio.run (e.g., loop issues)
         logger.critical(f"Unhandled exception during asyncio.run: {e}", exc_info=True)
