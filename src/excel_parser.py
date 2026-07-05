import io
import requests
import datetime
import pandas as pd
from rapidfuzz import process, utils
import config

def load_excel_data():
    """Loads slots schedule from Excel file / Google Sheets URL."""
    try:
        # Load slots schedule (local or Google Sheets URL)
        if config.USE_GOOGLE_SHEET and config.SLOTS_URL:
            print(f"Downloading latest schedule from Google Sheets...")
            response = requests.get(config.SLOTS_URL)
            response.raise_for_status()
            slots_df = pd.read_excel(io.BytesIO(response.content), sheet_name=config.SLOTS_SHEET_NAME)
        else:
            print(f"Loading local schedule: {config.SLOTS_FILE}")
            slots_df = pd.read_excel(config.SLOTS_FILE)
    except Exception as e:
        # Fallback to local file if configured and URL fails
        if config.USE_GOOGLE_SHEET and config.SLOTS_FILE:
            print(f"[WARNING] Google Sheets download failed ({e}). Falling back to local slots.xlsx.")
            try:
                slots_df = pd.read_excel(config.SLOTS_FILE)
            except Exception as local_err:
                raise RuntimeError(f"Failed to read local slots fallback: {local_err}")
        else:
            raise RuntimeError(f"Failed to read slots schedule: {e}")

    return slots_df

def sanitize_name(name):
    """Sanitizes names by stripping whitespace and converting to string."""
    if pd.isna(name) or not isinstance(name, str):
        return ""
    return name.strip()

def find_best_match(signup_name, volunteer_names, threshold=config.FUZZY_MATCH_THRESHOLD):
    """
    Finds the best matching volunteer name for a given signup name.
    First tries exact match, then prefix match, then fuzzy matching.
    """
    signup_name_clean = sanitize_name(signup_name)
    if not signup_name_clean:
        return None, 0.0

    # Lowercase lists for exact/prefix comparisons
    volunteer_names_clean = [sanitize_name(n) for n in volunteer_names]
    volunteer_names_lower = [n.lower() for n in volunteer_names_clean]
    signup_name_lower = signup_name_clean.lower()

    # 1. Try Exact Case-Insensitive Match
    if signup_name_lower in volunteer_names_lower:
        idx = volunteer_names_lower.index(signup_name_lower)
        return volunteer_names_clean[idx], 100.0

    # 2. Try Prefix Match (e.g. "Alice" matches "Alice Smith")
    prefix_matches = [
        val for val in volunteer_names_clean 
        if val.lower().startswith(signup_name_lower)
    ]
    if len(prefix_matches) == 1:
        return prefix_matches[0], 95.0

    # 3. Try Fuzzy Match
    match = process.extractOne(
        signup_name_clean, 
        volunteer_names_clean, 
        processor=utils.default_process
    )
    if match:
        matched_name, score, _ = match
        if score >= threshold:
            return matched_name, score

    return None, 0.0

def parse_assignments(target_date=None):
    """
    Parses slots schedule. Can filter by target_date (format 'YYYY-MM-DD').
    Returns:
        tuple: (assignments list, list of vacant slots)
    """
    slots_df = load_excel_data()
    assignments = []
    vacant_slots = []

    # Format target_date to string if it's a date object
    if isinstance(target_date, (datetime.date, datetime.datetime)):
        target_date = target_date.strftime("%Y-%m-%d")

    # Detect Layout Format
    is_simple_format = "Volunteer Name" in slots_df.columns and "Slot" in slots_df.columns

    if is_simple_format:
        print("Detected Simple Schedule Format.")
        for _, row in slots_df.iterrows():
            slot_date = str(row.get("Date", "")).split()[0] # strip timestamp if present
            slot_desc = row.get("Slot", "N/A")
            signup_name = sanitize_name(row.get("Volunteer Name", ""))

            # Filter by target date if specified
            if target_date and slot_date != target_date:
                continue

            # Skip slot if explicitly marked as 'No Mass' (case-insensitive)
            if signup_name.lower() == "no mass":
                continue

            slot_info = {
                "date": slot_date,
                "slot": slot_desc,
                "signup_name": signup_name,
                "status": "vacant"
            }

            if not signup_name or signup_name.upper() in ["VACANT", "EMPTY", "OPEN", "NONE"]:
                vacant_slots.append(slot_info)
                assignments.append(slot_info)
            else:
                slot_info["status"] = "filled"
                assignments.append(slot_info)

    else:
        print("Detected Hierarchical Google Sheets Format.")
        # Parse hierarchical sheet structure
        months = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]
        current_month = None
        
        # Estimate year from sheet headers or column name
        year = datetime.date.today().year
        first_col_name = str(slots_df.columns[0])
        for word in first_col_name.split():
            if word.isdigit() and len(word) == 4:
                year = int(word)
                break

        for _, row in slots_df.iterrows():
            col0_val = row.iloc[0]
            if pd.isna(col0_val):
                continue
            
            val_str = str(col0_val).strip()
            
            # Detect month rows
            if val_str.lower() in months:
                current_month = val_str
                continue
                
            # Detect day numbers
            try:
                day_num = int(float(val_str))
                is_day = True
            except ValueError:
                is_day = False
                
            if current_month and is_day:
                month_num = months.index(current_month.lower()) + 1
                slot_date_obj = datetime.date(year, month_num, day_num)
                slot_date = slot_date_obj.strftime("%Y-%m-%d")

                # Filter by target date if specified
                if target_date and slot_date != target_date:
                    continue

                slots_to_parse = [
                    {"name": "09:30 AM Bagels", "value": row.iloc[1]},
                    {"name": "11:30 AM Bagels", "value": row.iloc[2]},
                    {"name": "Baker", "value": row.iloc[3]}
                ]

                for slot in slots_to_parse:
                    val = slot["value"]
                    
                    # Skip slot if it is explicitly marked as 'No Mass' (case-insensitive)
                    if not pd.isna(val) and isinstance(val, str) and val.strip().lower() == "no mass":
                        continue
                    
                    # Split multiple names (e.g. "Julia and Isaac")
                    signups = []
                    if not pd.isna(val) and isinstance(val, str) and val.strip():
                        raw_val = val.strip()
                        for delimiter in [" and ", " & ", " / ", " + "]:
                            raw_val = raw_val.replace(delimiter, ",")
                        signups = [s.strip() for s in raw_val.split(",") if s.strip()]

                    if not signups:
                        slot_info = {
                            "date": slot_date,
                            "slot": slot["name"],
                            "signup_name": "",
                            "status": "vacant"
                        }
                        assignments.append(slot_info)
                        vacant_slots.append(slot_info)
                    else:
                        for s_name in signups:
                            if s_name.upper() in ["VACANT", "EMPTY", "OPEN", "NONE"]:
                                slot_info = {
                                    "date": slot_date,
                                    "slot": slot["name"],
                                    "signup_name": s_name,
                                    "status": "vacant"
                                }
                                assignments.append(slot_info)
                                vacant_slots.append(slot_info)
                            else:
                                slot_info = {
                                    "date": slot_date,
                                    "slot": slot["name"],
                                    "signup_name": s_name,
                                    "status": "filled"
                                }
                                assignments.append(slot_info)

    return assignments, vacant_slots
