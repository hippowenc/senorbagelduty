import sys
from pathlib import Path

# Add src/ directory to system path
src_path = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(src_path))

from groupme_client import GroupMeClient
import config

try:
    config.validate_config()
    client = GroupMeClient()
    
    print("Checking authenticated user...")
    me = client.get_me()
    print(f"Authenticated as: {me.get('name')} (ID: {me.get('id')})")
    
    print("\nFetching your groups (up to 100)...")
    groups = client.list_groups()
    if not groups:
        print("No groups found.")
    else:
        print("Groups:")
        for idx, g in enumerate(groups, 1):
            print(f"  {idx}. Name: {g['name']} | ID: {g['id']} | Members: {g['member_count']}")
            
except Exception as e:
    print(f"An error occurred: {e}")
