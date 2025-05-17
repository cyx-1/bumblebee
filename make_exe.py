#!/usr/bin/env python3
import os
import subprocess
import sys


def build_executable():
    """Build the Bumblebee executable using PyInstaller."""
    print("Building Bumblebee executable...")

    # Determine command to run
    cmd = [
        "pyinstaller",
        "--clean",
        "--onefile",
        "--name",
        "bumblebee",
        "src/main.py",
        "--hidden-import=yaml",
        "--hidden-import=yaml.loader",
        "--hidden-import=docx",
        "--paths=.venv/Lib/site-packages",
    ]

    print("Command to run:", " ".join(cmd))

    # Run PyInstaller
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        print("Error: PyInstaller failed to build the executable.")
        sys.exit(1)

    # Output completion message
    print("\nBuild completed!")
    print("Executable can be found in the 'dist' folder.")
    print()

    # Get the correct path format for the user's platform
    user_profile = os.path.expanduser("~")

    print("Don't forget to set up your configuration file:")
    print(f"- Copy bumblebee.yaml.template to {user_profile}\\bumblebee.yaml")
    print("- Edit the file to set the correct paths")


if __name__ == "__main__":
    build_executable()
