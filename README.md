# 🥯 Bagel Duty Manager

An automated serverless workflow that reads your weekly signup schedule directly from Google Sheets, matches volunteers against active GroupMe group members, and pings them with `@mentions` using a GroupMe Bot.

---

## 🚀 Key Features

*   **Google Sheets Integration**: Pulls the live schedule dynamically from your shared Google Sheet (no API keys, tokens, or service accounts required!).
*   **Direct Member Matching**: Automatically matches signup names directly against your active GroupMe group member profiles (no local volunteer database files to maintain).
*   **"No Mass" Exclusion**: If a slot's cell contains `"No Mass"` (case-insensitive), it is completely ignored by the script, excluding it from both volunteer reminders and group chat vacancy pings.
*   **Custom Hierarchical Sheet Parser**: Custom-tailored to read the signup template where months are rows, days are listed under them, and slots are column headers (`09:30 AM Bagels`, `11:30 AM Bagels`, and `Baker`).
*   **Smart Name Splitting**: Handles joint signups (e.g. `"Julia and Isaac"`, `"Julia & Isaac"`, `"Julia / Isaac"`), separating and pinging both volunteers individually.
*   **Group Chat Reminders**: Formats a single weekly post and tags all scheduled volunteers with standard GroupMe `@mentions` (highlighting their names and sending phone notifications).
*   **Private Admin Reports**: Private crash tracebacks and mismatch summaries (e.g., if a volunteer signs up but isn't in the GroupMe chat) are direct-messaged (DM) directly to you, keeping the public chat clean.
*   **Automated Sunday Targeter**: Computes the upcoming Sunday relative to the current run date.

---

## 🛠️ GitHub Actions Setup (Recommended)

Run this script automatically in the cloud on a schedule so that your personal computer does not need to be turned on.

### 1. Repository Preparation
1. Create a **private** repository on GitHub.
2. Commit and push the project files to your repository. 
   *(The `.gitignore` file will automatically prevent committing the local `.env` file containing secret keys).*

### 2. Configure Repository Secrets
In your GitHub repository, navigate to **Settings** -> **Secrets and variables** -> **Actions** -> **New repository secret**. 

Create the following secrets:
*   `GROUPME_ACCESS_TOKEN`: Your Personal Developer Access Token (retrieve from [dev.groupme.com](https://dev.groupme.com/)). Used read-only to map member names to internal user IDs.
*   `BOT_ID`: Your GroupMe Bot ID (obtain from the Bots section of the developer portal). Used to post reminders and alerts.
*   `GROUPME_GROUP_ID`: Your target GroupMe group ID.
*   `ADMIN_USER_ID`: Your personal GroupMe user ID (used for private reports and crash notifications).
*   `SLOTS_URL`: The export link to your Google Sheet:
    `https://docs.google.com/spreadsheets/d/YOUR_SPREADSHEET_ID/export?format=xlsx`
    *(Ensure your Google Sheet link sharing setting is set to **"Anyone with the link can view"**).*

### 3. Automated Weekly Runs
The GitHub Actions workflow [.github/workflows/bagel_duty.yml](.github/workflows/bagel_duty.yml) is set to execute:
*   **Automatically**: Every Saturday morning at **9:00 AM Central Time** (14:00 UTC).
*   **Manually**: Go to the **Actions** tab in your repository, select **Bagel Duty Manager Reminder Job**, click **Run workflow**, and optionally enter a custom date override (format: `YYYY-MM-DD`).

---

## 💻 Running Locally

### 1. Initialize Virtual Environment
A local virtual environment has been pre-configured in the project directory. To activate:
```bash
source venv/bin/activate
```

### 2. Configure Credentials (`.env`)
Create/modify the local `.env` file in the project root:
```ini
GROUPME_ACCESS_TOKEN=your_valid_token_here
BOT_ID=your_bot_id_here
GROUPME_GROUP_ID=your_group_id_here
ADMIN_USER_ID=your_user_id_here
SLOTS_URL=https://docs.google.com/spreadsheets/d/1rYFZR8L2WJPEvFbSSr5lk6KLdGsnlHvOZMeQc5jC5DA/export?format=xlsx
SLOTS_SHEET_NAME=Summer 26
USE_GOOGLE_SHEET=true
```

> [!TIP]
> To find your personal **User ID** and **Group IDs**, verify your token inside `.env` and run the helper script:
> ```bash
> python tests/test_groupme.py
> ```

---

## 🧪 Testing and Previews

*   **Live Preview**: Fetch the live Google Sheet, run direct matching against active GroupMe members, and preview the pings, reminders, and admin reports without sending anything to the chat:
    ```bash
    python tests/test_live_sheets.py
    ```
*   **Offline Mock Tests**: Run the suite of mock unit tests verifying date matching, empty slot announcements, and error reports:
    ```bash
    python tests/test_workflow_mock.py
    ```
*   **Execute Live Trigger**: Manually run the live workflow for the upcoming Sunday:
    ```bash
    python src/main.py
    ```
    *To force run for a specific Sunday:*
    ```bash
    python src/main.py 2026-07-12
    ```
