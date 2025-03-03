import secrets
import string
import argparse
import logging
from services.db_service import DBService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def generate_api_key(length=32):
    """
    Generate a secure random API key.
    
    Args:
        length: Length of the API key to generate
        
    Returns:
        A secure random string
    """
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def main():
    """Main function to generate and store an API key."""
    parser = argparse.ArgumentParser(description='Generate a new API key for the Fact Checker API')
    parser.add_argument('--name', type=str, help='Name or description for this API key')
    parser.add_argument('--length', type=int, default=32, help='Length of the API key (default: 32)')
    args = parser.parse_args()
    
    # Generate a new API key
    api_key = generate_api_key(args.length)
    
    # Store the API key in the database
    db_service = DBService()
    success = db_service.add_api_key(api_key, args.name)
    
    if success:
        logger.info(f"Generated new API key: {api_key}")
        print(f"\nAPI Key: {api_key}")
        print("\nStore this key securely. It will not be shown again.")
        print(f"Description: {args.name or 'No description provided'}")
    else:
        logger.error("Failed to add API key to database. Try again.")
        print("Error: Failed to generate API key. Please try again.")

if __name__ == "__main__":
    main() 