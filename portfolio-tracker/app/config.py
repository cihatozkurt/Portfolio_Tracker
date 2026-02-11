import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///data/portfolio.db")
    
    # API Keys
    ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
    
    # App Settings
    APP_NAME = "Portfolio Tracker"
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"