import sys
from pathlib import Path

# Add src/ directory to system path
src_path = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(src_path))

import unittest
from unittest.mock import MagicMock, patch
import main
import config

class TestBagelDutyWorkflow(unittest.TestCase):
    
    def setUp(self):
        # Reset config settings before each test
        self.orig_group_id = config.GROUPME_GROUP_ID
        self.orig_admin_id = config.ADMIN_USER_ID
        self.orig_bot_id = config.BOT_ID
        config.GROUPME_GROUP_ID = "test_group_id_123"
        config.ADMIN_USER_ID = "111"
        config.BOT_ID = "bot_123"

    def tearDown(self):
        # Restore original config settings
        config.GROUPME_GROUP_ID = self.orig_group_id
        config.ADMIN_USER_ID = self.orig_admin_id
        config.BOT_ID = self.orig_bot_id

    @patch('main.GroupMeClient')
    @patch('excel_parser.load_excel_data')
    def test_mock_full_workflow(self, mock_load_excel, mock_client_class):
        # 1. Setup mock Excel data (only slots schedule is needed now)
        import pandas as pd
        mock_slots = pd.DataFrame({
            "Date": ["2026-07-12", "2026-07-12", "2026-07-12", "2026-07-12"],
            "Slot": ["09:00 AM - Setup", "10:00 AM - Shift 1", "11:00 AM - Shift 2", "12:00 PM - Shift 3"],
            "Volunteer Name": [
                "Owen Chipman",   # Match exact GroupMe name
                "Alice",          # Fuzzy/prefix match Alice Smith on GroupMe
                "Dave Miller",    # Unmatched in GroupMe members
                "VACANT"          # Vacant slot
            ]
        })
        mock_load_excel.return_value = mock_slots

        # 2. Setup mock GroupMe Client
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        # Mock group members list in GroupMe
        mock_client.get_group_members.return_value = [
            {"user_id": "111", "name": "Owen Chipman", "nickname": "Owen C"},
            {"user_id": "222", "name": "Alice Smith", "nickname": "AliceS"},
            {"user_id": "333", "name": "Bob Jones", "nickname": "Bobby"},
        ]
        
        # DMs sent recorder (used for admin reports)
        dms_sent = []
        def mock_send_dm(recipient_id, text):
            dms_sent.append((recipient_id, text))
            return {"meta": {"code": 200}}
        mock_client.send_dm.side_effect = mock_send_dm
        
        # Bot posts sent recorder
        bot_posts_sent = []
        def mock_post_as_bot(text, bot_id=None, attachments=None):
            bot_posts_sent.append((text, bot_id or config.BOT_ID, attachments))
            return {"meta": {"code": 200}}
        mock_client.post_as_bot.side_effect = mock_post_as_bot

        # 3. Run the workflow
        main.run_workflow("2026-07-12")

        # 4. Verify results
        # We expect two bot posts: 
        # 1. Reminders message with mentions
        # 2. Vacancy alert message
        self.assertEqual(len(bot_posts_sent), 2)
        
        # Validate Reminders Post
        reminder_post = [p for p in bot_posts_sent if "Volunteer Reminders" in p[0]][0]
        self.assertEqual(reminder_post[1], "bot_123") # check Bot ID
        
        # Note: it will use the matched GroupMe nicknames/names
        self.assertIn("@Owen C", reminder_post[0])
        self.assertIn("@AliceS", reminder_post[0])
        self.assertIn("Dave Miller", reminder_post[0]) # Still listed in text but as unmatched (no @)
        
        # Check mentions attachment structure
        attachments = reminder_post[2]
        self.assertEqual(len(attachments), 1)
        self.assertEqual(attachments[0]["type"], "mentions")
        self.assertIn("111", attachments[0]["user_ids"]) # Owen's user ID
        self.assertIn("222", attachments[0]["user_ids"]) # Alice's user ID
        
        # Verify indices in loci
        loci = attachments[0]["loci"]
        self.assertEqual(len(loci), 2)
        # Check first mention (@Owen C) starts where predicted
        first_mention_text = "@Owen C"
        start_idx, length = loci[0]
        self.assertEqual(reminder_post[0][start_idx:start_idx+length], first_mention_text)

        # Validate Vacancy Alert Post
        vacancy_post = [p for p in bot_posts_sent if "We still need volunteers" in p[0]][0]
        self.assertIn("12:00 PM - Shift 3", vacancy_post[0])

        # Validate Admin report DM (Dave Miller should be reported since he is not in the GroupMe group list)
        self.assertEqual(len(dms_sent), 1)
        self.assertEqual(dms_sent[0][0], "111")
        self.assertIn("Dave Miller", dms_sent[0][1])

    @patch('main.GroupMeClient')
    @patch('excel_parser.load_excel_data')
    @patch('sys.argv', ['main.py', '2026-07-12'])
    def test_missing_files_triggers_crash_report(self, mock_load_excel, mock_client_class):
        # Simulate missing files by raising FileNotFoundError
        mock_load_excel.side_effect = FileNotFoundError("slots.xlsx not found")
        
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        # DMs sent recorder
        dms_sent = []
        mock_client.send_dm.side_effect = lambda recipient_id, text: dms_sent.append((recipient_id, text))
        
        # Run main() which handles crashes
        with self.assertRaises(SystemExit) as cm:
            main.main()
            
        # Verify it exited with code 1
        self.assertEqual(cm.exception.code, 1)
        
        # Verify it sent a crash report to the admin
        self.assertEqual(len(dms_sent), 1)
        self.assertEqual(dms_sent[0][0], "111") # Admin ID
        self.assertIn("Bagel Duty Manager Script Crash Alert!", dms_sent[0][1])

    @patch('main.GroupMeClient')
    @patch('excel_parser.load_excel_data')
    def test_groupme_api_failures_dont_crash_script(self, mock_load_excel, mock_client_class):
        # Setup valid Excel data
        import pandas as pd
        mock_slots = pd.DataFrame({
            "Date": ["2026-07-12"],
            "Slot": ["09:00 AM - Setup"],
            "Volunteer Name": ["Owen Chipman"]
        })
        mock_load_excel.return_value = mock_slots

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        # Mock group members list in GroupMe
        mock_client.get_group_members.return_value = [
            {"user_id": "111", "name": "Owen Chipman", "nickname": "Owen C"},
        ]
        
        # Simulate Bot API failure
        mock_client.post_as_bot.side_effect = Exception("Bot Service Offline")
        # Record DMs
        dms_sent = []
        mock_client.send_dm.side_effect = lambda recipient_id, text: dms_sent.append((recipient_id, text))

        # Run the workflow - it should catch the exception internally and NOT crash
        try:
            main.run_workflow("2026-07-12")
        except Exception as e:
            self.fail(f"run_workflow raised an exception when Bot failed: {e}")
            
        # Ensure post_as_bot was called
        mock_client.post_as_bot.assert_any_call(unittest.mock.ANY, attachments=unittest.mock.ANY)
        # Ensure it reported to the admin
        self.assertEqual(len(dms_sent), 1)
        self.assertEqual(dms_sent[0][0], "111")
        self.assertIn("Bot Service Offline", dms_sent[0][1])

    @patch('main.GroupMeClient')
    @patch('excel_parser.load_excel_data')
    def test_no_mass_slots_are_excluded(self, mock_load_excel, mock_client_class):
        import pandas as pd
        # Simulate hierarchical sheet format
        mock_slots = pd.DataFrame(
            [
                ["July", None, None, None, None],
                [12.0, "No Mass", "Owen Chipman", "VACANT", False]
            ],
            columns=["Summer 2026 Hospitality Signups", "Unnamed: 1", "Unnamed: 2", "Unnamed: 3", "Unnamed: 4"]
        )
        mock_load_excel.return_value = mock_slots

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.get_group_members.return_value = [
            {"user_id": "111", "name": "Owen Chipman", "nickname": "Owen C"},
        ]
        
        bot_posts = []
        mock_client.post_as_bot.side_effect = lambda text, bot_id=None, attachments=None: bot_posts.append(text)

        # Run workflow targeting July 12
        main.run_workflow("2026-07-12")

        # Check reminder post
        reminder_posts = [p for p in bot_posts if "Volunteer Reminders" in p]
        self.assertEqual(len(reminder_posts), 1)
        self.assertIn("11:30 AM Bagels: @Owen C", reminder_posts[0])
        self.assertNotIn("09:30 AM Bagels", reminder_posts[0])

        # Check vacancy post
        vacancy_posts = [p for p in bot_posts if "We still need volunteers" in p]
        self.assertEqual(len(vacancy_posts), 1)
        self.assertIn("Baker", vacancy_posts[0])
        self.assertNotIn("09:30 AM Bagels", vacancy_posts[0])

if __name__ == '__main__':
    unittest.main()
