#!/usr/bin/env python3
from typing import Tuple, Dict, Any, Optional
import smtplib
from email.message import EmailMessage
from datetime import datetime
from openai import OpenAI
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled


def send_email_notification(message: str, sender_email: str, sender_password: str, recipient_email: str = 'yexinchen@gmail.com') -> bool:
    """
    Send an email notification using Gmail SMTP.

    Args:
        message (str): The message to send (can be HTML)
        sender_email (str): Your Gmail address
        sender_password (str): Your Gmail app password
        recipient_email (str, optional): Recipient's email address. Defaults to 'yexinchen@gmail.com'
    """
    # Setup email
    msg = EmailMessage()
    # Add both HTML and plain text versions
    msg.set_content("Please view this email with an HTML-capable email client.")
    msg.add_alternative(message, subtype='html')

    msg['Subject'] = f"Bumblebee - {datetime.today().strftime('%Y-%m-%d %H:%M:%S')}"
    msg['From'] = sender_email
    msg['To'] = recipient_email

    # Send email using Gmail SMTP
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(sender_email, sender_password)
            smtp.send_message(msg)
            print(f"Email sent successfully to {recipient_email}")
            return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False


def get_youtube_transcript(video_url: str) -> Tuple[bool, str]:
    """
    Fetches the transcript for a given YouTube video URL.

    Args:
        video_url (str): The URL of the YouTube video.

    Returns:
        Tuple[bool, str]: A tuple containing a success flag and the transcript string or an error message.
    """
    try:
        video_id = ''
        if "v=" in video_url:
            video_id = video_url.split("v=")[1].split("&")[0]
        elif "youtu.be/" in video_url:
            video_id = video_url.split("youtu.be/")[1].split("?")[0]
        else:
            return False, "Invalid YouTube URL format."

        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        transcript_text = " ".join([item['text'] for item in transcript_list])
        return True, transcript_text
    except NoTranscriptFound:
        return False, f"No transcript found for video ID: {video_id}."
    except TranscriptsDisabled:
        return False, f"Transcripts are disabled for video ID: {video_id}."
    except Exception as e:
        return False, f"Failed to retrieve transcript: {str(e)}"


def get_ai_response(query: str, api_key: str, model: str = "grok-3-beta") -> Tuple[bool, str]:
    """
    Get AI-generated response for a query using X.AI's API.

    Args:
        query (str): The question or prompt to send to the AI
        api_key (str): X.AI API key
        model (str, optional): The model to use. Defaults to "grok-3-beta"

    Returns:
        tuple: (success: bool, response: str)
    """
    try:
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.x.ai/v1",
        )
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that provides accurate, well-researched info. Respond using a html div section, not a complete html",
                },
                {"role": "user", "content": query},
            ],
        )

        # Extract the response
        response = completion.choices[0].message.content or ""  # Convert None to empty string if needed
        print(f"AI response: {response}")
        return True, response
    except Exception as e:
        error_msg = f"Failed to get AI response: {str(e)}"
        print(error_msg)
        return False, error_msg


def process_query_and_send_email(query: str, openai_key: str, sender_email: str, sender_password: str, recipient_email: str) -> bool:
    """
    Process a query through AI and send the results via email.

    Args:
        query (str): The question to ask the AI
        openai_key (str): X.AI API key
        sender_email (str): Gmail address to send from
        sender_password (str): Gmail app password
        recipient_email (str, optional): Recipient's email address
    """
    success, ai_response = get_ai_response(query, openai_key)
    if success:
        truncated_query = query[:500] + "..." if len(query) > 500 else query
        message = f'''
    <html>
    <head>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 0; padding: 8px; }}
        .header {{ color: #333; font-size: 16px; border-bottom: 1px solid #ddd; padding-bottom: 4px; margin-bottom: 8px; }}
        .content {{ display: inline-block; margin-left: 8px; }}
        .timestamp {{ color: #888; font-size: 12px; margin-top: 8px; border-top: 1px solid #ddd; padding-top: 4px; }}
    </style>
    </head>
    <body>
        <div class="header">Ask Bumblebee: {truncated_query}</div>
        {ai_response}
        <div class="timestamp">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
    </body>
    </html>
    '''
        return send_email_notification(message, sender_email, sender_password, recipient_email)
    return False
