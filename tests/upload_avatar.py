import sys
import os
import mimetypes
import requests
from pathlib import Path
from dotenv import load_dotenv

# Add src/ directory to system path
src_path = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(src_path))

import config

def upload_image(image_path):
    # Load .env variables from root
    env_path = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(dotenv_path=env_path)
    
    token = os.getenv("GROUPME_ACCESS_TOKEN")
    if not token:
        print("Error: GROUPME_ACCESS_TOKEN not found in .env file.")
        sys.exit(1)
        
    path = Path(image_path)
    if not path.exists():
        print(f"Error: File '{image_path}' does not exist.")
        sys.exit(1)
        
    # Guess mime type
    mime_type, _ = mimetypes.guess_type(image_path)
    if not mime_type or not mime_type.startswith("image/"):
        print("Error: File must be an image (PNG, JPEG, etc.).")
        sys.exit(1)

    print(f"Uploading '{path.name}' ({mime_type}) to GroupMe Image Service...")
    
    url = "https://image.groupme.com/pictures"
    headers = {
        "X-Access-Token": token,
        "Content-Type": mime_type
    }
    
    try:
        with open(path, "rb") as f:
            response = requests.post(url, headers=headers, data=f)
            response.raise_for_status()
            
        data = response.json()
        picture_url = data.get("payload", {}).get("picture_url")
        print("\n🎉 Upload Successful!")
        print(f"GroupMe Image URL:\n{picture_url}")
        print("\nYou can now copy this URL and paste it into dev.groupme.com as your Bot's Avatar URL.")
        return picture_url
    except Exception as e:
        print(f"Upload failed: {e}")
        if 'response' in locals() and response.text:
            print(f"Response: {response.text}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: ./venv/bin/python3 upload_avatar.py <path_to_image>")
        sys.exit(1)
    upload_image(sys.argv[1])
