import sqlite3
import os
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DBService:
    """Service for handling database operations."""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the database service.
        
        Args:
            db_path: Path to the SQLite database file. If None, uses default path.
        """
        if db_path is None:
            # Use default path
            self.db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'factchecker.db')
        else:
            self.db_path = db_path
            
        # Ensure the data directory exists
        data_dir = os.path.dirname(self.db_path)
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
            logger.info(f"Created data directory: {data_dir}")
            
        # Check if database exists, if not initialize it
        if not os.path.exists(self.db_path):
            logger.info(f"Database not found at {self.db_path}, initializing...")
            self._init_db()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection."""
        return sqlite3.connect(self.db_path)
    
    def _init_db(self):
        """Initialize the database with required tables."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Create API keys table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used TIMESTAMP,
            is_active BOOLEAN DEFAULT 1
        )
        ''')
        
        # Create usage statistics table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS usage_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            api_key_id INTEGER,
            endpoint TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            response_time_ms INTEGER,
            status_code INTEGER,
            FOREIGN KEY (api_key_id) REFERENCES api_keys (id)
        )
        ''')
        
        # Create rate limiting table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS rate_limits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            api_key_id INTEGER,
            hour_timestamp TEXT NOT NULL,
            request_count INTEGER DEFAULT 1,
            FOREIGN KEY (api_key_id) REFERENCES api_keys (id),
            UNIQUE(api_key_id, hour_timestamp)
        )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    
    def validate_api_key(self, api_key: str) -> bool:
        """
        Validate if an API key exists and is active.
        
        Args:
            api_key: The API key to validate
            
        Returns:
            True if the key is valid and active, False otherwise
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT id FROM api_keys WHERE key = ? AND is_active = 1",
            (api_key,)
        )
        result = cursor.fetchone()
        
        # Update last_used timestamp if key exists
        if result:
            cursor.execute(
                "UPDATE api_keys SET last_used = CURRENT_TIMESTAMP WHERE id = ?",
                (result[0],)
            )
            conn.commit()
        
        conn.close()
        return result is not None
    
    def get_api_key_id(self, api_key: str) -> Optional[int]:
        """
        Get the ID of an API key.
        
        Args:
            api_key: The API key to look up
            
        Returns:
            The ID of the API key, or None if not found
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM api_keys WHERE key = ?", (api_key,))
        result = cursor.fetchone()
        
        conn.close()
        return result[0] if result else None
    
    def log_request(self, api_key: str, endpoint: str, response_time_ms: int, status_code: int):
        """
        Log an API request.
        
        Args:
            api_key: The API key used for the request
            endpoint: The endpoint that was accessed
            response_time_ms: Response time in milliseconds
            status_code: HTTP status code of the response
        """
        api_key_id = self.get_api_key_id(api_key)
        if not api_key_id:
            logger.warning(f"Attempted to log request for unknown API key: {api_key[:5]}...")
            return
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO usage_stats (api_key_id, endpoint, response_time_ms, status_code) VALUES (?, ?, ?, ?)",
            (api_key_id, endpoint, response_time_ms, status_code)
        )
        
        conn.commit()
        conn.close()
    
    def check_rate_limit(self, api_key: str, max_requests_per_hour: int = 100) -> Tuple[bool, int]:
        """
        Check if an API key has exceeded its rate limit.
        
        Args:
            api_key: The API key to check
            max_requests_per_hour: Maximum allowed requests per hour
            
        Returns:
            Tuple of (is_allowed, current_count)
        """
        api_key_id = self.get_api_key_id(api_key)
        if not api_key_id:
            logger.warning(f"Rate limit check for unknown API key: {api_key[:5]}...")
            return False, 0
        
        # Get current hour timestamp (YYYY-MM-DD-HH format)
        current_hour = datetime.now().strftime("%Y-%m-%d-%H")
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Check if entry exists for this hour
        cursor.execute(
            "SELECT request_count FROM rate_limits WHERE api_key_id = ? AND hour_timestamp = ?",
            (api_key_id, current_hour)
        )
        result = cursor.fetchone()
        
        if result:
            current_count = result[0]
            # If under limit, increment the counter
            if current_count < max_requests_per_hour:
                cursor.execute(
                    "UPDATE rate_limits SET request_count = request_count + 1 WHERE api_key_id = ? AND hour_timestamp = ?",
                    (api_key_id, current_hour)
                )
                current_count += 1
                is_allowed = True
            else:
                is_allowed = False
        else:
            # First request this hour
            cursor.execute(
                "INSERT INTO rate_limits (api_key_id, hour_timestamp, request_count) VALUES (?, ?, 1)",
                (api_key_id, current_hour)
            )
            current_count = 1
            is_allowed = True
        
        conn.commit()
        conn.close()
        
        return is_allowed, current_count
    
    def add_api_key(self, api_key: str, name: Optional[str] = None) -> bool:
        """
        Add a new API key to the database.
        
        Args:
            api_key: The API key to add
            name: Optional name/description for the key
            
        Returns:
            True if added successfully, False if key already exists
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "INSERT INTO api_keys (key, name) VALUES (?, ?)",
                (api_key, name)
            )
            conn.commit()
            success = True
        except sqlite3.IntegrityError:
            logger.warning(f"API key already exists: {api_key[:5]}...")
            success = False
        
        conn.close()
        return success
    
    def get_usage_stats(self, api_key: Optional[str] = None, days: int = 7) -> List[Dict[str, Any]]:
        """
        Get usage statistics.
        
        Args:
            api_key: Optional API key to filter by
            days: Number of days to look back
            
        Returns:
            List of usage statistics
        """
        conn = self._get_connection()
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        cursor = conn.cursor()
        
        if api_key:
            api_key_id = self.get_api_key_id(api_key)
            if not api_key_id:
                logger.warning(f"Usage stats requested for unknown API key: {api_key[:5]}...")
                return []
            
            cursor.execute(
                """
                SELECT endpoint, COUNT(*) as count, AVG(response_time_ms) as avg_response_time,
                       strftime('%Y-%m-%d', timestamp) as date
                FROM usage_stats
                WHERE api_key_id = ? AND timestamp >= datetime('now', '-' || ? || ' days')
                GROUP BY endpoint, date
                ORDER BY date DESC, count DESC
                """,
                (api_key_id, days)
            )
        else:
            cursor.execute(
                """
                SELECT endpoint, COUNT(*) as count, AVG(response_time_ms) as avg_response_time,
                       strftime('%Y-%m-%d', timestamp) as date
                FROM usage_stats
                WHERE timestamp >= datetime('now', '-' || ? || ' days')
                GROUP BY endpoint, date
                ORDER BY date DESC, count DESC
                """,
                (days,)
            )
        
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return results 