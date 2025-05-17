# Bumblebee

Bumblebee is a project to monitor an OneDrive folder which will receive MP3 audio files or transcription files generated from Apple Watch and phone. This tool enables users to transcribe audio files in a configurable OneDrive location and perform various configurable tasks.

Example tasks include:
- Retrieve stock research information on a company
- Summarize a book

## Installation

### Prerequisites
- Python 3.8 or higher
- Windows 10 or newer
- pipx has uv and pyinstaller installed
- Google app password created via: https://myaccount.google.com/apppasswords


### Setup
1. Clone this repository
2. Run uv script to install dependencies:
   ```
   uv pip install .
   ```
3. Copy and modify the configuration template:
   ```
   copy bumblebee.yaml.template %USERPROFILE%\bumblebee.yaml
   ```
4. Edit the `%USERPROFILE%\bumblebee.yaml` file to configure your settings

### Building the Executable
Run the build script to create the executable:
```
build.bat
```
The executable will be available in the `dist` folder.

## Usage

### Configuration
Before running the application, you need to set up a configuration file:

1. Copy the template configuration file to your home directory:
   ```
   copy bumblebee.yaml.template %USERPROFILE%\bumblebee.yaml
   ```

2. Edit the `%USERPROFILE%\bumblebee.yaml` file to set the correct paths:
   - `monitor_path`: The OneDrive folder to monitor
   - `processed_path`: Where to move processed files (optional)
   - `check_interval`: How often to check for new files (in seconds)

### Running the Application
Run the executable:
```
dist\bumblebee.exe
```

The application will:
1. Load your configuration
2. Start monitoring the specified folder
3. Print information about newly detected files
4. Move processed files to a dated subfolder in the processed directory

### Testing
For testing purposes, you can use the included test scripts:

1. Set up a test environment:
   ```
   setup_test_env.bat
   ```

2. Generate test files to trigger the monitoring:
   ```
   generate_test_files.bat
   ```

## Features
The current version implements the following must-have features from the PRD:

1. **Basic Setup**
   - Uses uv to manage packages
   - Creates an exe executable for simple usage
   - Core application framework

2. **OneDrive Folder Monitoring**
   - Configurable path monitoring using a YAML config file
   - Support for MP3, Word documents, and text files
   - Automatic file processing and organization
   - OneDrive refresh triggering
   - Moves processed files to a dated subfolder