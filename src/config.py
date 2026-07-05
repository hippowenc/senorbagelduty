import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root (parent of src)
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

GROUPME_ACCESS_TOKEN = os.getenv("GROUPME_ACCESS_TOKEN")
GROUPME_GROUP_ID = os.getenv("GROUPME_GROUP_ID")
ADMIN_USER_ID = os.getenv("ADMIN_USER_ID")
BOT_ID = os.getenv("BOT_ID")

# Excel file paths
BASE_DIR = Path(__file__).resolve().parent.parent
SLOTS_FILE = os.getenv("SLOTS_FILE", str(BASE_DIR / "slots.xlsx"))

# Google Sheets Configuration
SLOTS_URL = os.getenv("SLOTS_URL", "https://docs.google.com/spreadsheets/d/1rYFZR8L2WJPEvFbSSr5lk6KLdGsnlHvOZMeQc5jC5DA/export?format=xlsx")
SLOTS_SHEET_NAME = os.getenv("SLOTS_SHEET_NAME", "Summer 26")
USE_GOOGLE_SHEET = os.getenv("USE_GOOGLE_SHEET", "true").lower() == "true"

# Match sensitivity (from 0 to 100, where 100 is exact match only)
FUZZY_MATCH_THRESHOLD = int(os.getenv("FUZZY_MATCH_THRESHOLD", "85"))

def validate_config():
    """Validates that crucial settings are present."""
    missing = []
    if not GROUPME_ACCESS_TOKEN:
        missing.append("GROUPME_ACCESS_TOKEN")
    if not BOT_ID or BOT_ID == "your_bot_id_here":
        missing.append("BOT_ID")
    
    if not GROUPME_GROUP_ID or GROUPME_GROUP_ID == "your_group_id_here":
        print("[WARNING] GROUPME_GROUP_ID is not configured. Some operations might be limited.")
    if not ADMIN_USER_ID or ADMIN_USER_ID == "your_user_id_here":
        print("[WARNING] ADMIN_USER_ID is not configured. Admin error alerts will not work.")
        
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
