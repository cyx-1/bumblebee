from datetime import datetime
import os
import imaplib
import email
from email.header import decode_header
from typing import Tuple, Dict, Any


def get_first_gmail_email_imap(gmail_user: str, app_password: str) -> Tuple[bool, Dict[str, Any]]:
    """
    Retrieve the first (most recent) email from Gmail using IMAP and app password.

    Args:
        gmail_user (str): Gmail email address
        app_password (str): Gmail app password (not regular password)

    Returns:
        Tuple[bool, Dict[str, Any]]: Success status and email data dictionary
    """
    try:
        # Connect to Gmail IMAP server
        mail = imaplib.IMAP4_SSL('imap.gmail.com')
        mail.login(gmail_user, app_password)

        # Select inbox
        mail.select('inbox')

        # Search for all emails and get the most recent one
        status, messages = mail.search(None, 'ALL')
        if status != 'OK' or not messages[0]:
            return False, {"error": "No emails found"}

        # Get the latest email ID
        email_ids = messages[0].split()
        latest_email_id = email_ids[-1]

        # Fetch the email
        status, msg_data = mail.fetch(latest_email_id, '(RFC822)')
        if status != 'OK':
            return False, {"error": "Failed to fetch email"}

        # Parse the email
        if isinstance(msg_data[0], tuple):
            email_body = msg_data[0][1]
        else:
            email_body = msg_data[0] if msg_data[0] is not None else b''
        email_message = email.message_from_bytes(email_body)

        # Extract email data
        email_data = {}

        # Get subject
        subject = email_message["Subject"]
        if subject:
            subject, encoding = decode_header(subject)[0]
            if isinstance(subject, bytes):
                subject = subject.decode(encoding or 'utf-8')
        email_data['subject'] = subject or 'No subject'

        # Get other headers
        email_data['from'] = email_message.get("From", "Unknown sender")
        email_data['to'] = email_message.get("To", "Unknown recipient")
        email_data['date'] = email_message.get("Date", "Unknown date")

        # Extract body
        body = ""
        if email_message.is_multipart():
            for part in email_message.walk():
                if part.get_content_type() == "text/plain":
                    payload = part.get_payload(decode=True)
                    if isinstance(payload, bytes):
                        body = payload.decode('utf-8')
                    elif isinstance(payload, str):
                        body = payload
                    break
        else:
            payload = email_message.get_payload(decode=True)
            if isinstance(payload, bytes):
                body = payload.decode('utf-8')
            elif isinstance(payload, str):
                body = payload
            else:
                body = ""

        email_data['body'] = body
        email_data['id'] = latest_email_id.decode('utf-8')
        email_data['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")

        # Close connection
        mail.close()
        mail.logout()

        return True, email_data

    except Exception as e:
        return False, {"error": f"Failed to retrieve Gmail email via IMAP: {str(e)}"}


def test():
    """
    Test function to retrieve the first Gmail email using app password
    """
    # You'll need to set these environment variables or pass them directly
    gmail_user = os.getenv('GMAIL_USER')  # your-email@gmail.com
    app_password = os.getenv('GMAIL_APP_PASSWORD')  # your 16-character app password

    if not gmail_user or not app_password:
        return "Error: Please set GMAIL_USER and GMAIL_APP_PASSWORD environment variables"

    success, email_data = get_first_gmail_email_imap(gmail_user, app_password)

    if success:
        subject = email_data.get('subject', 'No subject')
        sender = email_data.get('from', 'Unknown sender')
        date = email_data.get('date', 'Unknown date')
        body_preview = email_data.get('body', '')[:200] + "..." if len(email_data.get('body', '')) > 200 else email_data.get('body', '')

        return f"""First Gmail email retrieved successfully at {email_data['timestamp']}:
Subject: {subject}
From: {sender}
Date: {date}
Body Preview: {body_preview}"""
    else:
        error_msg = email_data.get('error', 'Unknown error')
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
        return f"Failed to retrieve Gmail email at {current_time}: {error_msg}"
