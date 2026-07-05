import uuid
import requests
import config

class GroupMeClient:
    def __init__(self, token=None):
        self.token = token or config.GROUPME_ACCESS_TOKEN
        self.base_url = "https://api.groupme.com/v3"
        self.headers = {
            "X-Access-Token": self.token,
            "Content-Type": "application/json"
        }

    def _get(self, endpoint, params=None):
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()

    def _post(self, endpoint, json_data):
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        response = requests.post(url, headers=self.headers, json=json_data)
        response.raise_for_status()
        return response.json()

    def list_groups(self):
        """Lists all groups the authenticated user is in. Useful for configuration."""
        data = self._get("groups", params={"per_page": 100})
        groups = []
        for g in data.get("response", []):
            groups.append({
                "id": g.get("id"),
                "name": g.get("name"),
                "member_count": len(g.get("members", []))
            })
        return groups

    def get_me(self):
        """Gets current authenticated user's profile info."""
        data = self._get("users/me")
        return data.get("response", {})

    def get_group_members(self, group_id):
        """Retrieves list of members for a specific group."""
        try:
            data = self._get(f"groups/{group_id}")
            group_info = data.get("response", {})
            if not group_info:
                return []
            
            members = []
            for m in group_info.get("members", []):
                members.append({
                    "user_id": m.get("user_id"),
                    "nickname": m.get("nickname"),
                    "name": m.get("name")
                })
            return members
        except Exception as e:
            print(f"Error fetching group members for group {group_id}: {e}")
            return []

    def send_dm(self, recipient_id, text):
        """Sends a Direct Message (DM) to a user."""
        payload = {
            "direct_message": {
                "source_guid": str(uuid.uuid4()),
                "recipient_id": str(recipient_id),
                "text": text
            }
        }
        return self._post("direct_messages", payload)



    def post_as_bot(self, text, bot_id=None, attachments=None):
        """Posts a message to a group chat using the Bot API (supports mentions)."""
        target_bot_id = bot_id or config.BOT_ID
        if not target_bot_id:
            raise ValueError("No Bot ID configured or provided.")
            
        url = f"{self.base_url}/bots/post"
        payload = {
            "bot_id": target_bot_id,
            "text": text
        }
        if attachments:
            payload["attachments"] = attachments
            
        # The bot post endpoint does not require the X-Access-Token header
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response
