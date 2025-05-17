# GitHub Copilot Instructions

## Global Instructions
1. When importing new libraries use uv and update pyproject.toml
2. When importing new libraries, make sure to also install available library stubs
3. assume that uv and pyinstaller are already installed via pipx
4. Since this project is using uv and pyproject.toml to manage package dependencies, do not use requirements.txt

### Command Line and Scripting

1. **Do NOT use PowerShell commands** for any terminal operations, script generation, or system interactions.
2. Use command line tools and shells like:
   - CMD (Windows Command Prompt)
   - Git Bash

### For All File Types

When working with any file type in this project, always follow these guidelines:

1. **Script Generation**: When generating scripts or commands, use CMD, NOT PowerShell.
2. **File System Operations**: Use platform-neutral commands or CMD-compatible commands for Windows.
3. **Installation Instructions**: Provide installation and setup steps without PowerShell dependencies.

### Programming and Development

1. **Windows-Specific Code**: When Windows-specific functionality is needed, use non-PowerShell approaches such as:
   - Standard library functions in the respective programming language
   - Command-line tools accessible via `cmd.exe`
   - Cross-platform libraries where possible
   
2. **DevOps and Automation**: Suggest GitHub Actions, batch files, or shell scripts instead of PowerShell scripts.

## Rationale

This project aims to maintain better cross-platform compatibility and to avoid PowerShell execution policy issues or dependencies on specific PowerShell versions.

---

**Note**: These instructions apply to all interactions with GitHub Copilot within this repository.
