import sys
import traceback
import datetime
from groupme_client import GroupMeClient
from excel_parser import parse_assignments, find_best_match
import config

def match_signup_to_groupme_user(signup_name, members):
    """
    Fuzzy-matches a signup name directly to a member in the GroupMe group.
    Returns: (user_id, GroupMe_display_name) or (None, None)
    """
    if not members or not signup_name:
        return None, None
        
    signup_name_clean = signup_name.strip().lower()

    # Step 1: Look for exact case-insensitive matches on name or nickname
    for m in members:
        g_name = (m.get("name") or "").strip().lower()
        g_nick = (m.get("nickname") or "").strip().lower()
        if signup_name_clean in [g_name, g_nick]:
            # Prefer nickname if present, else fallback to name
            display_name = m.get("nickname") or m.get("name")
            return m.get("user_id"), display_name

    # Step 2: Build a flat list of display names to check
    names_to_check = []
    name_to_member_map = {}
    for m in members:
        u_id = m.get("user_id")
        n = (m.get("name") or "").strip()
        nk = (m.get("nickname") or "").strip()
        
        if n:
            names_to_check.append(n)
            name_to_member_map[n] = m
        if nk and nk != n:
            names_to_check.append(nk)
            name_to_member_map[nk] = m

    # Step 3: Try fuzzy matching against all GroupMe display names/nicknames
    matched_name, score = find_best_match(signup_name, names_to_check)
    if matched_name and score >= config.FUZZY_MATCH_THRESHOLD:
        member = name_to_member_map[matched_name]
        display_name = member.get("nickname") or member.get("name")
        print(f"Fuzzy matched signup '{signup_name}' to GroupMe member '{display_name}' (Score: {score:.1f})")
        return member.get("user_id"), display_name

    return None, None

def format_display_date(date_str):
    """Converts a YYYY-MM-DD date string to a Month DD, YYYY display string."""
    try:
        date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        return date_obj.strftime("%B %d, %Y")
    except Exception:
        return date_str

def format_group_reminders(filled_assignments, target_date, members):
    """
    Formats a single message reminding all matched volunteers and builds GroupMe mentions.
    Returns: (text_message, attachments, reminded_count, missing_users)
    """
    display_date = format_display_date(target_date)
    text_lines = [f"Volunteer Reminders for Sunday {display_date}:"]
    user_ids = []
    loci = []
    reminded_count = 0
    missing_users = []
    
    for a in filled_assignments:
        slot_name = a["slot"]
        signup_name = a["signup_name"]
        
        user_id, matched_name = match_signup_to_groupme_user(signup_name, members)
        
        if user_id:
            line_start = f"• {slot_name}: "
            mention_text = f"@{matched_name}"
            
            # Calculate character offset in joined string
            current_len = sum(len(line) + 1 for line in text_lines)
            start_idx = current_len + len(line_start)
            
            text_lines.append(f"{line_start}{mention_text}")
            
            user_ids.append(user_id)
            loci.append([start_idx, len(mention_text)])
            reminded_count += 1
        else:
            # Still list them in the text even if we couldn't resolve their GroupMe profile
            text_lines.append(f"• {slot_name}: {signup_name}")
            missing_users.append(signup_name)
            
    text_lines.append("\nThank you for volunteering! 🥯")
    message_text = "\n".join(text_lines)
    
    attachments = []
    if user_ids:
        attachments.append({
            "type": "mentions",
            "user_ids": user_ids,
            "loci": loci
        })
        
    return message_text, attachments, reminded_count, missing_users

def run_workflow(target_date=None):
    print("Starting Bagel Duty Manager workflow (Direct Match)...")
    
    # 1. Validate Config
    config.validate_config()
    client = GroupMeClient()

    # 2. Determine target Sunday date
    if not target_date:
        today = datetime.date.today()
        days_to_sunday = (6 - today.weekday()) % 7
        upcoming_sunday = today + datetime.timedelta(days=days_to_sunday)
        target_date = upcoming_sunday.strftime("%Y-%m-%d")
        print(f"Targeting upcoming Sunday: {target_date}")
    else:
        print(f"Targeting date override: {target_date}")

    # 3. Parse schedules
    print("Parsing Excel schedules...")
    assignments, vacant_slots = parse_assignments(target_date)

    # If no slots found for this date, print message and exit
    if not assignments:
        print(f"No slots found or configured for target date: {target_date}. Exiting.")
        return

    # 4. Fetch GroupMe group members to build name->id lookup
    print(f"Fetching members for group ID: {config.GROUPME_GROUP_ID}...")
    members = client.get_group_members(config.GROUPME_GROUP_ID)
    if not members:
        print("[WARNING] Could not fetch group members. Mentions will not be matched.")

    reminded_count = 0
    missing_account_users = []
    filled_assignments = [a for a in assignments if a["status"] == "filled"]

    # 5. Notify volunteers for filled slots via Bot Post with @mentions
    if filled_assignments:
        print("Formatting group reminders with mentions...")
        reminder_text, reminder_attachments, reminded_count, missing_account_users = format_group_reminders(
            filled_assignments, target_date, members
        )
                
        try:
            print("Posting volunteer reminders to group chat as bot...")
            client.post_as_bot(reminder_text, attachments=reminder_attachments)
            print("Group reminders posted successfully.")
        except Exception as e:
            print(f"Failed to post group reminders as bot: {e}")
            # Fallback to report all matched names as errors to admin if bot failed
            missing_account_users.extend([f"{a['signup_name']} (Bot Error: {e})" for a in filled_assignments if a["signup_name"] not in missing_account_users])

    display_date = format_display_date(target_date)

    # 6. Alert Group Chat for vacant slots via Bot Post
    if vacant_slots:
        print("Vacant slots found. Preparing group alert...")
        alert_lines = [f"We still need volunteers for this Sunday {display_date}:"]
        for vs in vacant_slots:
            alert_lines.append(f"• {vs['slot']}")
        alert_lines.append("\nPlease sign up if you can make it! 🥯")
        group_msg = "\n".join(alert_lines)

        try:
            print("Posting vacant alert to group chat as bot...")
            client.post_as_bot(group_msg)
            print("Group vacancy alert posted successfully.")
        except Exception as e:
            print(f"Failed to post group vacancy alert as bot: {e}")

    # 7. Notify Administrator of discrepancies / errors (private DM via user token)
    admin_notif_lines = []
    if missing_account_users:
        admin_notif_lines.append("⚠️ Signups not matched to any GroupMe member profiles:")
        for name in missing_account_users:
            admin_notif_lines.append(f"  - {name}")

    if admin_notif_lines and config.ADMIN_USER_ID and config.ADMIN_USER_ID != "your_user_id_here":
        admin_msg = f"Bagel Duty Manager Report for {display_date}:\n" + "\n".join(admin_notif_lines)
        try:
            print("Sending report DM to admin Owen...")
            client.send_dm(config.ADMIN_USER_ID, admin_msg)
        except Exception as e:
            print(f"Failed to send report DM to Admin: {e}")

    print(f"Workflow finished. Reminded: {reminded_count} volunteers. Vacant slots: {len(vacant_slots)}. Issues: {len(missing_account_users)}.")

def main():
    try:
        target_date = None
        if len(sys.argv) > 1:
            target_date = sys.argv[1]
        run_workflow(target_date)
    except Exception as e:
        error_msg = f"💥 Bagel Duty Manager crashed!\nError: {e}\n\nTraceback:\n{traceback.format_exc()}"
        print(error_msg, file=sys.stderr)
        
        # Try to notify admin on failure
        if config.ADMIN_USER_ID and config.ADMIN_USER_ID != "your_user_id_here":
            try:
                temp_client = GroupMeClient()
                temp_client.send_dm(
                    config.ADMIN_USER_ID, 
                    f"⚠️ Bagel Duty Manager Script Crash Alert!\n\nError details: {str(e)[:400]}..."
                )
                print("Admin crash notification sent.")
            except Exception as admin_err:
                print(f"Could not notify admin of crash: {admin_err}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
