# filepath: backend/tools/gmail_tool.py
# Gmail API integration for sending application emails.
# Requires credentials/gmail_credentials.json and credentials/token.json
# Run setup_gmail.py first to get the token.

import os
import base64
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.readonly'
]

TOKEN_PATH = os.path.join("credentials", "token.json")
CREDENTIALS_PATH = os.path.join("credentials", "gmail_credentials.json")


def get_gmail_service():
    """
    Authenticate and return a Gmail API service object.
    Uses credentials/token.json (created by setup_gmail.py).
    """
    creds = None

    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("Refreshing expired Gmail token...")
            creds.refresh(Request())
            # Save refreshed token
            with open(TOKEN_PATH, 'w') as f:
                f.write(creds.to_json())
        else:
            raise RuntimeError(
                "Gmail not authenticated. Run setup_gmail.py first to generate token.json"
            )

    service = build('gmail', 'v1', credentials=creds)
    return service


def send_email(to: str, subject: str, body: str, sender_name: str = "HirePilot-AI") -> dict:
    """
    Send an email via Gmail API.
    Returns the sent message metadata dict on success.
    Raises on failure.
    """
    service = get_gmail_service()

    message = MIMEMultipart()
    message['to'] = to
    message['subject'] = subject
    message.attach(MIMEText(body, 'plain'))

    # Encode
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')

    try:
        result = service.users().messages().send(
            userId='me',
            body={'raw': raw}
        ).execute()
        logger.info(f"Email sent to {to}. Message ID: {result.get('id')}")
        return result
    except Exception as e:
        logger.error(f"Failed to send email to {to}: {e}")
        raise


def send_test_email(to: str) -> bool:
    """Send a test email to verify Gmail works. Returns True on success."""
    try:
        send_email(
            to=to,
            subject="HirePilot-AI Test Email",
            body="This is a test email from HirePilot-AI to verify Gmail integration is working."
        )
        return True
    except Exception as e:
        logger.error(f"Test email failed: {e}")
        return False
