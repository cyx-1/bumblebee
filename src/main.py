"""
Bumblebee - Audio file monitoring and processing system
Main entry point for the application
"""

import os
import sys
import time
import shutil
from datetime import datetime
from pathlib import Path
import yaml
from docx import Document
from faster_whisper import WhisperModel  # type: ignore
from src.util_bumblebee import process_query_and_send_email


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

            # Transcribe the audio file
            segments, _ = self.model.transcribe(audio_file, beam_size=5)

            # Join all segments into final text
            transcription = " ".join(segment.text for segment in segments)

            if not transcription.strip():
                return False, "Transcription produced no text"

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
                print(f"Configuration file not found: {self.config_path}")
                print("Please create a configuration file based on the template.")
                sys.exit(1)

            with open(self.config_path, 'r') as file:
                config = yaml.safe_load(file)
                print(f"Configuration loaded from {self.config_path}")
                return config
        except Exception as e:
            print(f"Error loading configuration: {str(e)}")
            sys.exit(1)

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
            return {
                'x.ai': ai_config.get('x.ai'),
            }
        except KeyError:
            print("Warning: AI configuration not found")
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
        Process a newly detected file

        Args:
            filepath: Full path to the file

        Returns:
            bool: Whether processing was successful
        """
        try:
            filename = os.path.basename(filepath)
            print(f"\nProcessing new file: {filename}")
            content = None

            # Create file info dictionary
            file_info = {'name': filename, 'type': None}

            # Process the file based on its type
            _, ext = os.path.splitext(filepath.lower())

            # Process text files
            if ext == '.txt':
                file_info['type'] = 'Text file'
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()

            # Process Word documents
            elif ext in [self.EXT_DOCX, self.EXT_DOC]:
                file_info['type'] = 'Word document'
                if ext == self.EXT_DOCX:
                    doc = Document(filepath)
                    content = '\n'.join([paragraph.text for paragraph in doc.paragraphs])
                else:
                    print("Note: .doc files are not supported, only .docx")
                    return False

            # Process MP3 files
            elif ext == '.mp3':
                file_info['type'] = 'MP3 audio'
                success, transcription = self.transcriber.transcribe(filepath)
                if success:
                    content = transcription
                else:
                    print(f"Transcription failed: {transcription}")
                    return False

            # Send content via email if we have content and email config
            if content and self.email_config.get('sender_email'):
                process_query_and_send_email(
                    query=content,
                    sender_email=self.email_config['sender_email'],
                    sender_password=self.email_config['sender_password'],
                    recipient_email=self.email_config.get('recipient_email'),
                    openai_key=self.ai_config.get('x.ai'),
                )

            # Create processed subfolder with date if needed
            date_folder = os.path.join(self.processed_path, datetime.now().strftime("%Y-%m-%d"))
            os.makedirs(date_folder, exist_ok=True)

            # Move file to processed folder
            target_path = os.path.join(date_folder, filename)
            shutil.move(filepath, target_path)
            print(f"\nMoved '{filename}' to {target_path}")

            return True
        except Exception as e:
            print(f"Error processing file {filepath}: {str(e)}")
            return False

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
                # Trigger OneDrive refresh
                self._refresh_onedrive()
                # Check for new files
                current_files = {os.path.join(self.monitor_path, f) for f in os.listdir(self.monitor_path) if os.path.isfile(os.path.join(self.monitor_path, f))}

                new_files = current_files - self.known_files
                new_supported_files = [f for f in new_files if self._is_supported_file(f)]

                # Process new files
                for filepath in new_supported_files:
                    if self._process_file(filepath):
                        processed_files.append(filepath)

                        # Update known files - remove processed files from known files
                        self.known_files = current_files - set(processed_files)

                if run_once:
                    return processed_files

                # Wait for the next check
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
        # Load configuration
        config = Configuration()

        # Get paths and settings from config
        monitor_path = config.get_monitor_path()
        processed_path = config.get_processed_path()
        check_interval = config.get_check_interval()
        email_config = config.get_email_config()
        ai_config = config.get_ai_config()
        print("Configuration loaded successfully.")
        print(f"Monitoring folder: {monitor_path}")
        print(f"Processed files will be moved to: {processed_path}")
        print(f"Checking for new files every {check_interval} seconds")

        # Create folder monitor and start watching
        monitor = FolderMonitor(
            monitor_path=monitor_path, processed_path=processed_path, check_interval=check_interval, email_config=email_config, ai_config=ai_config
        )

        # Start monitoring (this runs indefinitely)
        monitor.start_monitoring()
    except KeyboardInterrupt:
        print("\nBumblebee application stopped by user.")
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
