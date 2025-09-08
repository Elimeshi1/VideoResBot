import sqlite3
import os
from datetime import datetime
from utils.logger import logger
from typing import List, Tuple, Optional, Dict, Any
from config.config import Config

class Database:
    """SQLite database manager for premium user functionality"""
    DB_FILE = Config.DATABASE_URL
    
    def __init__(self):
        try:
            # Ensure data directory exists - handle case where dirname is empty
            db_dir = os.path.dirname(self.DB_FILE)
            if db_dir:  # Only create directory if it's not empty
                os.makedirs(db_dir, exist_ok=True)
            
            # Initialize database and create tables if they don't exist
            self.conn = sqlite3.connect(self.DB_FILE)
            self.cursor = self.conn.cursor()
            self._create_tables()
            
            logger.info(f"[✅] Database initialized successfully at {os.path.abspath(self.DB_FILE)}")
        except Exception as e:
            logger.error(f"[❌] Database initialization error: {e}")
            # Create fallback connection
            self.conn = None
            self.cursor = None
        
    def _create_tables(self):
        """Create necessary database tables if they don't exist"""
        try:
            if not self.conn or not self.cursor:
                logger.error("[❌] Cannot create tables - no database connection")
                return
                
            # Users table
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                is_premium BOOLEAN NOT NULL DEFAULT 0,
                premium_expiry TIMESTAMP,
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                max_channels INTEGER DEFAULT 0,
                is_banned BOOLEAN NOT NULL DEFAULT 0,
                ban_reason TEXT,
                user_channel_id INTEGER
            )
            ''')
            
            # Channels table
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS channels (
                channel_id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                added_date TIMESTAMP NOT NULL,
                expiry_date TIMESTAMP NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
            ''')
            
            
            self.conn.commit()
        except Exception as e:
            logger.error(f"[❌] Error creating database tables: {e}")
            
    def _ensure_connection(self) -> bool:
        """Ensure database connection is active, reconnect if needed"""
        if self.conn is None:
            try:
                # Ensure data directory exists again before reconnecting
                db_dir = os.path.dirname(self.DB_FILE)
                if db_dir:
                    os.makedirs(db_dir, exist_ok=True)
                    logger.info(f"[📁] Database directory ensured at: {os.path.abspath(db_dir)}")
                
                self.conn = sqlite3.connect(self.DB_FILE)
                self.cursor = self.conn.cursor()
                self._create_tables()  # Ensure tables exist
                logger.info("[🔄] Database connection reestablished")
                return True
            except Exception as e:
                logger.error(f"[❌] Failed to reconnect to database: {e}")
                return False
        return True
            
    def add_user(self, user_id: int, is_premium: bool = False, premium_expiry: Optional[datetime] = None, max_channels: int = 0) -> bool:
        """Add a new user or update existing user"""
        try:
            if not self._ensure_connection():
                return False
                
            # Get current time
            now = datetime.now().isoformat()
            
            # Check if user already exists
            self.cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
            exists = self.cursor.fetchone()
            
            if not exists:
                # Insert new user
                self.cursor.execute(
                    "INSERT INTO users (user_id, is_premium, premium_expiry, created_at, updated_at, max_channels) VALUES (?, ?, ?, ?, ?, ?)",
                    (user_id, is_premium, premium_expiry.isoformat() if premium_expiry else None, now, now, max_channels)
                )
                logger.info(f"[✅] User {user_id} added as regular user to database")
            
            self.conn.commit()
            return True
        
        except Exception as e:
            logger.error(f"[❌] Error adding user {user_id}: {e}")
            return False
            
    def set_user_premium(self, user_id: int, is_premium: int = 1, max_channels: int = 1, months: int = 1) -> bool:
        """Set a user's premium status with specified number of allowed channels and duration in months"""
        try:
            if not self._ensure_connection():
                return False
            
            now = datetime.now()
            # Premium lasts for the specified number of months
            expiry = datetime.fromtimestamp(now.timestamp() + months * 31 * 24 * 3600)
            
            # Check if the user exists
            self.cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
            exists = self.cursor.fetchone()
            
            if exists:
                # Update existing user
                self.cursor.execute(
                    "UPDATE users SET is_premium = ?, premium_expiry = ?, updated_at = ?, max_channels = ? WHERE user_id = ?",
                    (is_premium, expiry.isoformat(), now.isoformat(), max_channels, user_id)
                )
            else:
                # Create new user
                self.cursor.execute(
                    "INSERT INTO users (user_id, is_premium, premium_expiry, created_at, updated_at, max_channels) VALUES (?, ?, ?, ?, ?, ?)",
                    (user_id, is_premium, expiry.isoformat(), now.isoformat(), now.isoformat(), max_channels)
                )
                
            self.conn.commit()
            logger.info(f"[✅] User {user_id} set as {'premium' if is_premium else 'regular'} with {max_channels} channels for {months} months until {expiry.isoformat()}")
            return True
        except Exception as e:
            logger.error(f"[❌] Error setting premium status for user {user_id}: {e}")
            return False
            
    def is_user_premium(self, user_id: int) -> bool:
        """Check if a user has premium status and it's not expired"""
        try:
            if not self._ensure_connection():
                return False
                
            self.cursor.execute(
                "SELECT is_premium, premium_expiry FROM users WHERE user_id = ?",
                (user_id,)
            )
            result = self.cursor.fetchone()
            
            if not result:
                return False
                
            is_premium, expiry_str = result
            
            # If not premium, return False
            if not is_premium:
                return False
                
            # Check if premium is expired
            expiry = datetime.fromisoformat(expiry_str)
            now = datetime.now()
            
            return now < expiry
        except Exception as e:
            logger.error(f"[❌] Error checking premium status for user {user_id}: {e}")
            return False
            
    def get_user_premium_details(self, user_id: int) -> Optional[Tuple[bool, Optional[str], int]]:
        """Retrieve premium status, expiry date (as string), and max channels for a user."""
        try:
            if not self._ensure_connection():
                return None
                
            self.cursor.execute(
                "SELECT is_premium, premium_expiry, max_channels FROM users WHERE user_id = ?",
                (user_id,)
            )
            result = self.cursor.fetchone()
            
            if not result:
                # User not found, return default non-premium state
                return (False, None, 0)
                
            is_premium_db, expiry_str, max_channels = result
            
            # Check if expired (similar logic to is_user_premium)
            is_currently_premium = False
            if is_premium_db:
                try:
                    expiry_dt = datetime.fromisoformat(expiry_str)
                    if datetime.now() < expiry_dt:
                        is_currently_premium = True
                except ValueError:
                    logger.error(f"[❌] Invalid expiry date format in DB for user {user_id}: {expiry_str}")
            
            # Return actual status, expiry string, and max channels
            return (is_currently_premium, expiry_str, max_channels if max_channels is not None else 0)
            
        except Exception as e:
            logger.error(f"[❌] Error getting premium details for user {user_id}: {e}")
            return None

    def add_channel(self, channel_id: int, user_id: int) -> bool:
        """Add a channel for a premium user"""
        try:
            if not self._ensure_connection():
                return False
                
            # First check if user is premium
            if not self.is_user_premium(user_id):
                logger.warning(f"[⚠️] User {user_id} is not premium, cannot add channel")
                return False
                
            # Get user's premium details including expiry date
            premium_details = self.get_user_premium_details(user_id)
            if not premium_details:
                logger.warning(f"[⚠️] User {user_id} premium details not found")
                return False
                
            _, premium_expiry_str, _ = premium_details
            if not premium_expiry_str:
                logger.warning(f"[⚠️] User {user_id} has no premium expiry date")
                return False
                
            premium_expiry = datetime.fromisoformat(premium_expiry_str)
            now = datetime.now()
            
            # Add or update channel with the same expiry date as premium
            self.cursor.execute(
                "INSERT OR REPLACE INTO channels (channel_id, user_id, added_date, expiry_date) VALUES (?, ?, ?, ?)",
                (channel_id, user_id, now.isoformat(), premium_expiry.isoformat())
            )
            self.conn.commit()
            logger.info(f"[📺] Channel {channel_id} added for user {user_id} until {premium_expiry.isoformat()}")
            return True
        except Exception as e:
            logger.error(f"[❌] Error adding channel {channel_id} for user {user_id}: {e}")
            return False
            
    def is_channel_active(self, channel_id: int) -> bool:
        """Check if a channel is active (owned by a premium user and not expired)"""
        try:
            if not self._ensure_connection():
                return False
                
            self.cursor.execute(
                "SELECT user_id, expiry_date FROM channels WHERE channel_id = ?",
                (channel_id,)
            )
            result = self.cursor.fetchone()
            
            if not result:
                return False
                
            user_id, expiry_str = result
            
            # Check if channel subscription is expired
            expiry = datetime.fromisoformat(expiry_str)
            now = datetime.now()
            
            if now >= expiry:
                return False
                
            # Check if user is still premium
            return self.is_user_premium(user_id)
        except Exception as e:
            logger.error(f"[❌] Error checking channel {channel_id} status: {e}")
            return False
            
    def get_user_channels(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all channels for a specific user with their details"""
        try:
            if not self._ensure_connection():
                return []
                
            self.cursor.execute(
                "SELECT channel_id FROM channels WHERE user_id = ?",
                (user_id,)
            )
            channels = []
            for row in self.cursor.fetchall():
                channel_id = row[0]
                channel_details = self.get_channel_details(user_id, channel_id)
                if channel_details:
                    channels.append(channel_details)
            return channels
        except Exception as e:
            logger.error(f"[❌] Error getting channels for user {user_id}: {e}")
            return []
            
    def get_channel_details(self, user_id: int, channel_id: int) -> Optional[Dict[str, Any]]:
        """Get details for a specific channel belonging to a specific user."""
        try:
            if not self._ensure_connection():
                return None
                
            self.cursor.execute(
                "SELECT added_date, expiry_date FROM channels WHERE user_id = ? AND channel_id = ?",
                (user_id, channel_id)
            )
            result = self.cursor.fetchone()
            
            if not result:
                return None # Channel not found or doesn't belong to user
                
            added_date_str, expiry_date_str = result
            expiry_dt = datetime.fromisoformat(expiry_date_str)
            channel_details = {
                 "channel_id": channel_id,
                 "user_id": user_id,
                 "added_date": datetime.fromisoformat(added_date_str),
                 "expiry_date": expiry_dt,
                 "is_active": datetime.now() < expiry_dt
            }
            return channel_details
            
        except Exception as e:
            logger.error(f"[❌] Error getting details for channel {channel_id}, user {user_id}: {e}")
            return None
            
    def get_max_channels(self, user_id: int) -> int:
        """Get the maximum number of channels a user is allowed to add"""
        try:
            if not self._ensure_connection():
                return 0
                
            # Get the maximum channels count
            self.cursor.execute(
                "SELECT max_channels FROM users WHERE user_id = ?",
                (user_id,)
            )
            result = self.cursor.fetchone()
            
            if result:
                return result[0]  # Return the first element of the tuple
            else:
                return 0
                
        except Exception as e:
            logger.error(f"[❌] Error getting maximum channels for user {user_id}: {e}")
            return 0
            
    def remove_channel(self, channel_id: int) -> bool:
        """Remove a channel from the database"""
        try:
            if not self._ensure_connection():
                return False
                
            self.cursor.execute("DELETE FROM channels WHERE channel_id = ?", (channel_id,))
            self.conn.commit()
            logger.info(f"[🗑️] Channel {channel_id} removed from database")
            return True
        except Exception as e:
            logger.error(f"[❌] Error removing channel {channel_id}: {e}")
            return False
            
    def upgrade_user_channels(self, user_id: int, new_max_channels: int) -> bool:
        """Upgrade a user's maximum number of allowed channels"""
        try:
            if not self._ensure_connection():
                return False
                
            # First check if user exists
            self.cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
            if not self.cursor.fetchone():
                logger.warning(f"[⚠️] Cannot upgrade max_channels for non-existent user {user_id}")
                return False
            
            # Update the user's maximum channels
            now = datetime.now().isoformat()
            self.cursor.execute(
                "UPDATE users SET max_channels = ?, updated_at = ? WHERE user_id = ?", 
                (new_max_channels, now, user_id)
            )
            self.conn.commit()
            
            # Check if update happened
            success = self.cursor.rowcount > 0
            if success:
                logger.info(f"[⬆️] Upgraded user {user_id} to {new_max_channels} max channels")
            else:
                logger.warning(f"[⚠️] User {user_id} max_channels update had no effect (no rows modified)")
            
            return success
                
        except Exception as e:
            logger.error(f"[❌] Error upgrading max_channels for user {user_id}: {e}")
            return False
            
    def cleanup_expired(self) -> None:
        """Clean up expired premium users and channels"""
        try:
            if not self._ensure_connection():
                return
                
            now = datetime.now().isoformat()
            
            # Set users with expired premium to non-premium
            self.cursor.execute(
                "UPDATE users SET is_premium = 0 WHERE is_premium = 1 AND premium_expiry < ?",
                (now,)
            )
            
            self.conn.commit()
            logger.info("[🧹] Cleaned up expired premium statuses")
        except Exception as e:
            logger.error(f"[❌] Error cleaning up expired data: {e}")
            
    def ban_user(self, user_id: int, reason: str) -> bool:
        """Ban a user with a specific reason"""
        try:
            if not self._ensure_connection():
                return False
                
            now = datetime.now().isoformat()
            
            # Check if user exists
            self.cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
            exists = self.cursor.fetchone()
            
            if exists:
                # Update existing user
                self.cursor.execute(
                    "UPDATE users SET is_banned = 1, ban_reason = ?, updated_at = ? WHERE user_id = ?",
                    (reason, now, user_id)
                )
            else:
                # Create new user with ban status
                self.cursor.execute(
                    "INSERT INTO users (user_id, is_banned, ban_reason, created_at, updated_at) VALUES (?, 1, ?, ?, ?)",
                    (user_id, reason, now, now)
                )
                
            self.conn.commit()
            logger.info(f"[🚫] User {user_id} banned with reason: {reason}")
            return True
        except Exception as e:
            logger.error(f"[❌] Error banning user {user_id}: {e}")
            return False
            
    def unban_user(self, user_id: int) -> bool:
        """Unban a user"""
        try:
            if not self._ensure_connection():
                return False
                
            now = datetime.now().isoformat()
            
            self.cursor.execute(
                "UPDATE users SET is_banned = 0, ban_reason = NULL, updated_at = ? WHERE user_id = ?",
                (now, user_id)
            )
            self.conn.commit()
            
            success = self.cursor.rowcount > 0
            if success:
                logger.info(f"[✅] User {user_id} unbanned successfully")
            else:
                logger.warning(f"[⚠️] User {user_id} not found or already unbanned")
            
            return success
        except Exception as e:
            logger.error(f"[❌] Error unbanning user {user_id}: {e}")
            return False
            
    def is_user_banned(self, user_id: int) -> tuple[bool, Optional[str]]:
        """Check if a user is banned and return the ban reason if banned"""
        try:
            if not self._ensure_connection():
                return False, None
                
            self.cursor.execute(
                "SELECT is_banned, ban_reason FROM users WHERE user_id = ?",
                (user_id,)
            )
            result = self.cursor.fetchone()
            
            if not result:
                return False, None
                
            is_banned, ban_reason = result
            return bool(is_banned), ban_reason
        except Exception as e:
            logger.error(f"[❌] Error checking ban status for user {user_id}: {e}")
            return False, None

    def set_user_channel(self, user_id: int, channel_id: int) -> bool:
        """Set the user's channel for receiving processed videos"""
        try:
            if not self._ensure_connection():
                return False
            
            now = datetime.now().isoformat()
            
            # Check if user exists, if not create them
            self.cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
            exists = self.cursor.fetchone()
            
            if exists:
                # Update existing user
                self.cursor.execute(
                    "UPDATE users SET user_channel_id = ?, updated_at = ? WHERE user_id = ?",
                    (channel_id, now, user_id)
                )
            else:
                # Create new user with channel
                self.cursor.execute(
                    "INSERT INTO users (user_id, user_channel_id, created_at, updated_at) VALUES (?, ?, ?, ?)",
                    (user_id, channel_id, now, now)
                )
            
            self.conn.commit()
            logger.info(f"[✅] Set channel {channel_id} for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"[❌] Error setting channel for user {user_id}: {e}")
            return False
    
    def get_user_channel(self, user_id: int) -> Optional[int]:
        """Get the user's configured channel ID"""
        try:
            if not self._ensure_connection():
                return None
            
            self.cursor.execute(
                "SELECT user_channel_id FROM users WHERE user_id = ?",
                (user_id,)
            )
            result = self.cursor.fetchone()
            
            if result and result[0]:
                return int(result[0])
            return None
        except Exception as e:
            logger.error(f"[❌] Error getting channel for user {user_id}: {e}")
            return None
    
    def has_user_channel(self, user_id: int) -> bool:
        """Check if user has a configured channel"""
        channel_id = self.get_user_channel(user_id)
        return channel_id is not None

    def close(self):
        """Close the database connection"""
        if self.conn:
            try:
                self.conn.close()
            except Exception as e:
                logger.error(f"[❌] Error closing database connection: {e}")

# Singleton instance
db = Database() 