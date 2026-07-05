import sys
from pathlib import Path

# Add src/ directory to system path
src_path = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(src_path))

import datetime
import json
from excel_parser import parse_assignments
from groupme_client import GroupMeClient
from main import format_group_reminders
import config

def preview_live_run():
    print("==================================================")
    print("       BAGEL DUTY MANAGER - LIVE PREVIEW           ")
    print("==================================================")
    
    # Calculate upcoming Sunday
    today = datetime.date.today()
    days_to_sunday = (6 - today.weekday()) % 7
    upcoming_sunday = today + datetime.timedelta(days=days_to_sunday)
    target_date = upcoming_sunday.strftime("%Y-%m-%d")
    
    print(f"Current local time: {datetime.datetime.now()}")
    print(f"Target Sunday: {target_date}\n")
    
    print(f"Downloading Google Sheets from: {config.SLOTS_URL}")
    print(f"Sheet Name: {config.SLOTS_SHEET_NAME}\n")
    
    try:
        # Enable Google Sheets downloading
        config.USE_GOOGLE_SHEET = True
        
        # Parse slots
        assignments, vacant_slots = parse_assignments(target_date)
        
        print("\n--- SCHEDULE PARSING RESULTS ---")
        print(f"Total slots parsed for {target_date}: {len(assignments)}")
        print(f"Vacant slots: {len(vacant_slots)}")
        
        # Fetch GroupMe members for preview matching
        print(f"\nFetching GroupMe members for group: {config.GROUPME_GROUP_ID}...")
        client = GroupMeClient()
        members = []
        try:
            members = client.get_group_members(config.GROUPME_GROUP_ID)
            print(f"Successfully loaded {len(members)} group members from GroupMe.")
        except Exception as api_err:
            print(f"[WARNING] Could not fetch GroupMe members ({api_err}). Using fallback dummy list for preview.")
            # Fallback dummy list for preview testing if token is invalid
            members = [
                {"user_id": "111", "name": "Owen Chipman", "nickname": "Owen C"},
                {"user_id": "222", "name": "Alice Smith", "nickname": "AliceS"},
                {"user_id": "333", "name": "Bob Jones", "nickname": "Bobby"}
            ]

        filled_assignments = [a for a in assignments if a["status"] == "filled"]
        
        print("\n--- GROUP REMINDERS PREVIEW ---")
        if filled_assignments:
            reminder_text, reminder_attachments, reminded_count, missing_users = format_group_reminders(
                filled_assignments, target_date, members
            )
            print("Message Text:\n" + reminder_text)
            print("\nAttachments (Mentions Payload):")
            print(json.dumps(reminder_attachments, indent=2))
            
            print(f"\nMatch Summary:")
            print(f"  - Pings generated: {reminded_count} volunteers")
            print(f"  - Unmatched names (no pings): {len(missing_users)}")
            for mu in missing_users:
                print(f"    * {mu}")
        else:
            print("  No volunteers signed up. No reminders will be posted.")
            
        print("\n--- GROUP CHAT VACANCY NOTIFICATION PREVIEW ---")
        if vacant_slots:
            alert_lines = [f"🥯 We still need volunteers for this Sunday {target_date}! 🥯"]
            for vs in vacant_slots:
                alert_lines.append(f"• {vs['slot']}")
            alert_lines.append("\nPlease sign up if you can make it!")
            print("\n".join(alert_lines))
        else:
            print("  All slots are filled! No group announcement needed.")
            
    except Exception as e:
        print(f"\n💥 Preview Failed with Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    preview_live_run()
