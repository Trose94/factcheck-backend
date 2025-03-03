import sqlite3
import os
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database file path
DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'factchecker.db')

def ensure_data_dir():
    """Ensure the data directory exists."""
    data_dir = os.path.dirname(DB_PATH)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        logger.info(f"Created data directory: {data_dir}")

def init_db():
    """Initialize the database with required tables."""
    ensure_data_dir()
    
    # Connect to database (will create if it doesn't exist)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    logger.info("Initializing database...")
    
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
    logger.info("Database initialized successfully")
    
    # Close connection
    conn.close()

def add_api_key(key, name=None):
    """
    Add a new API key to the database.
    
    Args:
        key: The API key to add
        name: Optional name/description for the key
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT INTO api_keys (key, name) VALUES (?, ?)",
            (key, name)
        )
        conn.commit()
        logger.info(f"Added new API key: {key[:5]}...")
    except sqlite3.IntegrityError:
        logger.warning(f"API key already exists: {key[:5]}...")
    finally:
        conn.close()

def list_api_keys():
    """List all API keys in the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, key, name, created_at, last_used, is_active FROM api_keys")
    keys = cursor.fetchall()
    
    conn.close()
    
    if not keys:
        logger.info("No API keys found in database")
        return []
    
    logger.info(f"Found {len(keys)} API keys")
    return keys

if __name__ == "__main__":
    # Initialize the database
    init_db()
    
    # Check if we need to add keys from environment
    from dotenv import load_dotenv
    load_dotenv()
    
    valid_api_keys = os.getenv("VALID_API_KEYS", "").split(",")
    if valid_api_keys and valid_api_keys[0]:
        logger.info("Adding API keys from environment variables")
        for i, key in enumerate(valid_api_keys):
            key = key.strip()
            if key:
                add_api_key(key, f"Key {i+1} from environment")
    
    # List all keys
    keys = list_api_keys()
    for key in keys:
        key_id, key_value, name, created, last_used, is_active = key
        print(f"ID: {key_id}, Key: {key_value[:5]}..., Name: {name}, Active: {bool(is_active)}") 