import os
import sys
import shutil

def install_launchers():
    local_bin = os.path.expanduser("~/.local/bin")
    os.makedirs(local_bin, exist_ok=True)

    project_root = os.path.dirname(os.path.abspath(__file__))
    python_exe = os.path.join(project_root, ".venv", "Scripts", "python.exe")
    script_path = os.path.join(project_root, "cli_agent.py")

    cmd_content = f'@echo off\n"{python_exe}" "{script_path}" %*\n'
    ps1_content = f'& "{python_exe}" "{script_path}" $args\n'
    
    # Git Bash / sh path formatting
    drive_letter = project_root[0].lower()
    git_python = f"/{drive_letter}{python_exe[2:].replace(chr(92), '/')}"
    git_script = f"/{drive_letter}{script_path[2:].replace(chr(92), '/')}"
    sh_content = f'#!/usr/bin/env sh\nexec "{git_python}" "{git_script}" "$@"\n'

    cmd_file = os.path.join(local_bin, "pulse.cmd")
    ps1_file = os.path.join(local_bin, "pulse.ps1")
    sh_file = os.path.join(local_bin, "pulse")

    with open(cmd_file, "w", encoding="utf-8") as f:
        f.write(cmd_content)

    with open(ps1_file, "w", encoding="utf-8") as f:
        f.write(ps1_content)

    with open(sh_file, "w", encoding="utf-8") as f:
        f.write(sh_content)

    print(f"Installed global pulse launchers to {local_bin}:")
    print(f"  - {cmd_file} (CMD)")
    print(f"  - {ps1_file} (PowerShell)")
    print(f"  - {sh_file} (Git Bash / sh)")
    print("\nYou can now open any terminal in any directory and run 'pulse'!")

if __name__ == "__main__":
    install_launchers()
