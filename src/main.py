"""
Bumblebee - Audio file monitoring and processing system
Main entry point for the application
"""

import os
import sys
import time
import re
import shutil
import yaml
from pathlib import Path
from docx import Document
from faster_whisper import WhisperModel  # type: ignore
from src.util_bumblebee import process_query_and_send_email, get_youtube_transcript


class AudioTranscriber:
    """Handles transcription of audio files using faster-whisper"""

    def __init__(self):
        """Initialize the transcriber with a small model for fast processing"""
        try:
            print("Initializing audio transcription model...")
            # Use small model for good balance of speed and accuracy
            self.model = WhisperModel("small", device="cpu", compute_type="int8")
            print("Audio transcription model loaded successfully")
        except Exception as e:
            print(f"Error initializing audio transcription model: {str(e)}")
            raise

    def transcribe(self, audio_file):
        """
        Transcribe an audio file to text

        Args:
            audio_file: Path to the audio file

        Returns:
            tuple: (success: bool, text: str)
            where text is the transcription if successful, or error message if not
        """
        try:
            print(f"Starting transcription of {os.path.basename(audio_file)}")
            segments, _ = self.model.transcribe(audio_file, beam_size=5)
            transcription = " ".join(segment.text for segment in segments)

            if not transcription.strip():
                print(f"Warning: Transcription for {audio_file} is empty.")
                return True, ""

            print("Transcription completed successfully")
            return True, transcription
        except Exception as e:
            error_msg = f"Transcription failed: {str(e)}"
            print(error_msg)
            return False, error_msg


class Configuration:
    """Configuration manager for Bumblebee.
    Loads and provides access to user configuration from bumblebee.yaml
    """

    def __init__(self):
        self.config_path = os.path.join(str(Path.home()), "bumblebee.yaml")
        self.config = self._load_config()

    def _load_config(self):
        """Load configuration from YAML file in user's home directory"""
        try:
            if not os.path.exists(self.config_path):
                print(f"Error: Configuration file not found at {self.config_path}")
                return {}
            with open(self.config_path, 'r', encoding='utf-8') as file:
                config_data = yaml.safe_load(file)
                return config_data if config_data else {}
        except Exception as e:
            print(f"Error loading configuration from {self.config_path}: {str(e)}")
            return {}

    def get_monitor_path(self):
        """Get the OneDrive folder path to monitor"""
        try:
            return self.config['onedrive']['monitor_path']
        except KeyError:
            print("Error: monitor_path not defined in configuration file")
            sys.exit(1)

    def get_processed_path(self):
        """Get the path where processed files should be moved"""
        try:
            return self.config['onedrive'].get('processed_path', os.path.join(self.get_monitor_path(), "processed"))
        except KeyError:
            return os.path.join(self.get_monitor_path(), "processed")

    def get_check_interval(self):
        """Get the interval in seconds for checking the folder"""
        try:
            return self.config['onedrive'].get('check_interval', 60)
        except KeyError:
            return 60  # Default to 60 seconds

    def get_email_config(self):
        """Get email configuration settings"""
        try:
            email_config = self.config.get('email', {})
            return {
                'sender_email': email_config.get('sender_email'),
                'sender_password': email_config.get('sender_password'),
                'recipient_email': email_config.get('recipient_email'),
            }
        except KeyError:
            print("Warning: Email configuration not found")
            return {}

    def get_ai_config(self):
        """Get AI configuration settings"""
        try:
            ai_config = self.config.get('ai', {})
            x_ai_settings = ai_config.get('x.ai', {})
            return {'x.ai': x_ai_settings}
        except KeyError:
            print("Warning: AI configuration not found or incomplete.")
            return {}


class FolderMonitor:
    """Monitor a folder for new files and process them"""

    EXT_DOCX = '.docx'
    EXT_DOC = '.doc'

    def __init__(self, monitor_path, processed_path, check_interval=60, email_config=None, ai_config=None):
        """
        Initialize the folder monitor

        Args:
            monitor_path: Path to the folder to monitor
            processed_path: Path to move processed files to
            check_interval: How often to check for new files (seconds)
            email_config: Dictionary containing email configuration
        """
        self.monitor_path = monitor_path
        self.processed_path = processed_path
        self.check_interval = check_interval
        self.email_config = email_config or {}
        self.ai_config = ai_config or {}
        self.known_files = set()
        self.supported_extensions = {'.mp3', '.txt', self.EXT_DOCX, self.EXT_DOC}

        # Initialize audio transcriber
        self.transcriber = AudioTranscriber()

        # Ensure the processed folder exists
        os.makedirs(self.processed_path, exist_ok=True)

        # Initialize by scanning existing files
        self._scan_existing_files()

    def _scan_existing_files(self):
        """Scan existing files to establish baseline"""
        try:
            self.known_files = {os.path.join(self.monitor_path, f) for f in os.listdir(self.monitor_path) if os.path.isfile(os.path.join(self.monitor_path, f))}
            print(f"Initial scan complete. Found {len(self.known_files)} existing files.")
        except FileNotFoundError:
            print(f"Warning: Monitor directory {self.monitor_path} not found. Creating it.")
            os.makedirs(self.monitor_path, exist_ok=True)
        except PermissionError:
            print(f"Error: Permission denied when accessing {self.monitor_path}")

    def _is_supported_file(self, filepath):
        """Check if the file is a supported type"""
        _, ext = os.path.splitext(filepath.lower())
        return ext in self.supported_extensions

    def _refresh_onedrive(self):
        """
        Create and remove a temporary folder to trigger OneDrive to refresh.
        This helps ensure OneDrive syncs remote changes to the local folder.
        """
        temp_folder = os.path.join(self.monitor_path, f"refresh_{int(time.time())}")

        try:
            # Create temporary folder
            os.makedirs(temp_folder)

            # Wait a moment for OneDrive to register the new folder
            time.sleep(2)

            if os.path.exists(temp_folder):
                os.chmod(temp_folder, 0o777)  # Change permissions to ensure deletion
                os.rmdir(temp_folder)

        except Exception as e:
            print(f"Warning: Could not refresh OneDrive: {str(e)}")

    def _process_file(self, filepath):
        """
        Process a newly detected file.
        If the file content contains a YouTube URL, it fetches the transcript,
        gets an AI summary, and emails it. Otherwise, it processes the file content directly.
        """
        try:
            filename = os.path.basename(filepath)
            print(f"\nProcessing new file: {filename}")
            file_content_query = ""
            _, ext = os.path.splitext(filepath.lower())

            if ext == '.txt':
                with open(filepath, 'r', encoding='utf-8') as f:
                    file_content_query = f.read()
            elif ext == self.EXT_DOCX:
                doc = Document(filepath)
                file_content_query = "\n".join([para.text for para in doc.paragraphs])
            elif ext == '.mp3':
                success, transcription_text = self.transcriber.transcribe(filepath)
                if success:
                    file_content_query = f"Summarize the following audio transcription: \n\n{transcription_text}"
                else:
                    print(f"Transcription failed for {filename}: {transcription_text}")
                    self._move_file(filepath, filename, "error_transcription")
                    return False
            else:
                print(f"Unsupported file type for AI processing: {ext} for file {filename}")
                self._move_file(filepath, filename, "unsupported")
                return False

            if not file_content_query.strip():
                print(f"No content to process for {filename}")
                self._move_file(filepath, filename, "empty_content")
                return False

            youtube_url_pattern = r"(https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)[\w\-=&?]+)"
            match = re.search(youtube_url_pattern, file_content_query)
            video_url_to_process = None
            current_query_to_process = file_content_query

            if match:
                video_url_to_process = match.group(0)
                print(f"Detected YouTube URL in {filename}: {video_url_to_process}")

                api_key = self.ai_config.get('x.ai', {})
                if not api_key:
                    print(f"Error: X.AI API key not configured for YouTube processing of {filename}.")
                    self._move_file(filepath, filename, "error_config")
                    return False

                print(f"Fetching transcript for {video_url_to_process}...")
                success_transcript, transcript_or_error = get_youtube_transcript(video_url_to_process)

                if success_transcript:
                    current_query_to_process = (
                        f"first provide a video summary, then provide detailed description for each topic in this video "
                        f"with precision including key points made and person who made the point. "
                        f"youtube video location: {video_url_to_process} The transcript: {transcript_or_error}"
                    )
                    print(f"Transcript fetched. Querying AI for summary and details of {video_url_to_process}.")
                else:
                    print(f"Error fetching transcript for {video_url_to_process}: {transcript_or_error}")
                    self._move_file(filepath, filename, "error_youtube_transcript")
                    return False

            print(f"Sending query to AI for {filename}: \"{current_query_to_process[:200]}...\"")

            sender_email = self.email_config.get('sender_email')
            sender_password = self.email_config.get('sender_password')
            recipient_email = self.email_config.get('recipient_email')

            api_key = self.ai_config.get('x.ai', {})

            if not all([sender_email, sender_password, recipient_email, api_key]):
                print(f"Error: Email or AI API key configuration is missing for processing {filename}.")
                self._move_file(filepath, filename, "error_config")
                return False

            email_sent = process_query_and_send_email(
                query=current_query_to_process, openai_key=api_key, sender_email=sender_email, sender_password=sender_password, recipient_email=recipient_email
            )

            if email_sent:
                print(f"Successfully processed {filename} and sent email.")
                self._move_file(filepath, filename, "processed")
                return True
            else:
                print(f"Failed to process {filename} (AI/email step).")
                self._move_file(filepath, filename, "error_ai_email")
                return False

        except Exception as e:
            print(f"Critical error processing file {filepath}: {str(e)}")
            self._move_file(filepath, os.path.basename(filepath), "critical_error")
            return False

    def _move_file(self, filepath, filename, status_folder_name="processed"):
        """Helper function to move files and update known_files set."""
        try:
            destination_folder = os.path.join(self.processed_path, status_folder_name)
            os.makedirs(destination_folder, exist_ok=True)

            base, ext = os.path.splitext(filename)
            counter = 1
            destination_path = os.path.join(destination_folder, filename)
            while os.path.exists(destination_path):
                destination_path = os.path.join(destination_folder, f"{base}_{counter}{ext}")
                counter += 1
                if counter > 100:
                    print(f"Error: Too many conflicting filenames for {filename} in {destination_folder}.")
                    return

            shutil.move(filepath, destination_path)
            print(f"Moved {filename} to {destination_path}")
            if filepath in self.known_files:
                self.known_files.remove(filepath)
        except Exception as e:
            print(f"Error moving file {filename} to {status_folder_name}: {e}")

    def start_monitoring(self, run_once=False):
        """
        Start monitoring the folder for new files

        Args:
            run_once: If True, check once and return. Otherwise, run continuously.

        Returns:
            List of processed files if run_once=True, otherwise runs indefinitely
        """
        processed_files = []

        try:
            print(f"Starting to monitor folder: {self.monitor_path}")
            print(f"Processed files will be moved to: {self.processed_path}")

            while True:
                self._refresh_onedrive()
                current_files = {os.path.join(self.monitor_path, f) for f in os.listdir(self.monitor_path) if os.path.isfile(os.path.join(self.monitor_path, f))}

                new_files = current_files - self.known_files
                new_supported_files = [f for f in new_files if self._is_supported_file(f)]

                for filepath in new_supported_files:
                    if self._process_file(filepath):
                        processed_files.append(filepath)
                        self.known_files = current_files - set(processed_files)

                if run_once:
                    return processed_files

                time.sleep(self.check_interval)

        except KeyboardInterrupt:
            print("\nMonitoring stopped by user.")
            return processed_files
        except Exception as e:
            print(f"Error during monitoring: {str(e)}")
            raise


def main():
    """Main function that serves as the entry point for the Bumblebee application.
    Loads configuration and starts monitoring the specified OneDrive folder.
    """
    print("Starting Bumblebee application...")
    print("Loading configuration...")

    try:
        config = Configuration()

        monitor_path = config.get_monitor_path()
        processed_path = config.get_processed_path()
        check_interval = config.get_check_interval()
        email_config = config.get_email_config()
        ai_config = config.get_ai_config()
        print("Configuration loaded successfully.")
        print(f"Monitoring folder: {monitor_path}")
        print(f"Processed files will be moved to: {processed_path}")
        print(f"Checking for new files every {check_interval} seconds")

        monitor = FolderMonitor(
            monitor_path=monitor_path, processed_path=processed_path, check_interval=check_interval, email_config=email_config, ai_config=ai_config
        )

        monitor.start_monitoring()
    except KeyboardInterrupt:
        print("\nBumblebee application stopped by user.")
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
