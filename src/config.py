"""Configuration for the Gemini chatbot."""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Configuration settings for the Gemini chatbot."""
    
    # GCP Settings
    PROJECT_ID = "expel-engineering-prod"
    LOCATION = "us-central1"
    
    # Model Settings
    DEFAULT_MODEL = "gemini-2.5-flash"  # Latest Gemini 2.5 Flash model with enhanced capabilities
    
    # Chat Settings
    MAX_HISTORY_LENGTH = 10  # Number of conversation turns to keep in memory
    
    @staticmethod
    def get_project_id() -> str:
        """Get the Google Cloud project ID from environment or config."""
        # Try environment variable first, then fall back to default
        return os.getenv("GOOGLE_CLOUD_PROJECT", Config.PROJECT_ID)
    
    @staticmethod
    def get_location() -> str:
        """Get the Google Cloud location from environment or config."""
        # Try environment variable first, then fall back to default
        return os.getenv("GOOGLE_CLOUD_LOCATION", Config.LOCATION)
