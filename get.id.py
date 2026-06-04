from google_auth_oauthlib.flow import InstalledAppFlow
from dotenv import load_dotenv
import os

load_dotenv()

client_config = {
    "installed": {
        "client_id": os.getenv("GOOGLE_CLOUD_ID"),
        "client_secret": os.getenv("GOOGLE_CLOUD_SECRET"),
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": ["http://localhost"]
    }
}

flow = InstalledAppFlow.from_client_config(
    client_config,
    scopes=['openid', 'email', 'profile']
)

credentials = flow.run_local_server(port=0)
print("id_token:", credentials.id_token)