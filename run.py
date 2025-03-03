import uvicorn
from config import settings

def main():
    """
    Main entry point for running the FastAPI application.
    Loads configuration and starts the uvicorn server.
    """
    # Print startup message
    print(f"Starting {settings.API_TITLE} v{settings.API_VERSION}")
    print(f"Server running at http://{settings.HOST}:{settings.PORT}")
    print("Press CTRL+C to stop the server")
    
    # Start the uvicorn server
    uvicorn.run(
        "app:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    main() 