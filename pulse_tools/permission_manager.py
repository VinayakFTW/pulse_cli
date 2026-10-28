import os
import re
import json
from typing import Tuple


class PermissionManager:
    """Manages workspace boundary enforcement and access control."""

    def __init__(self, workspace_root: str | None = None, settings_filename: str = "pulse_settings.json"):
        self.workspace_root = os.path.realpath(os.path.abspath(workspace_root or os.getcwd()))
        self.session_approved_dirs: set[str] = set()
        self.settings = self._load_settings(settings_filename)

    def _load_settings(self, filename: str) -> dict:
        """Loads settings from active workspace or user home directory ~/.pulse/."""
        candidates = [
            os.path.join(self.workspace_root,".pulse", filename),
            os.path.expanduser(f"~/.pulse/{filename}")
        ]
        for path in candidates:
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        return json.load(f)
                except Exception as e:
                    print(f"Warning: Failed to load {path}: {e}")
        return {
            "permissions": {
                "allowed_directories": [],
                "require_hitl_for_external_access": True,
                "allow_external_reads": False,
                "allow_external_writes": False,
                "auto_approve_external": False
            }
        }

    def is_within_workspace(self, target_path: str) -> bool:
        """Checks if target_path resolves within the active workspace."""
        try:
            if not os.path.isabs(target_path):
                target_path = os.path.join(self.workspace_root, target_path)
            resolved = os.path.realpath(os.path.abspath(target_path))
            return os.path.commonpath([resolved, self.workspace_root]) == self.workspace_root
        except (ValueError, Exception):
            return False

    def check_path_access(self, target_path: str, is_write: bool = False, prompt_callback=None) -> Tuple[bool, str]:
        """
        Evaluates whether access to target_path is allowed.
        Returns (is_allowed, reason_or_error_message).
        """
        if not os.path.isabs(target_path):
            target_path = os.path.join(self.workspace_root, target_path)
        resolved = os.path.realpath(os.path.abspath(target_path))

        if self.is_within_workspace(resolved):
            return True, "within_workspace"

        perms = self.settings.get("permissions", {})
        auto_approve = perms.get("auto_approve_external", False) or perms.get("auto_approv_external", False)

        if not perms.get("require_hitl_for_external_access", True) or auto_approve:
            return True, "settings_override"

        if not is_write and perms.get("allow_external_reads", False):
            return True, "settings_read_allowed"

        if is_write and perms.get("allow_external_writes", False):
            return True, "settings_write_allowed"

        for allowed in perms.get("allowed_directories", []):
            try:
                res_allowed = os.path.realpath(os.path.abspath(allowed))
                if os.path.commonpath([resolved, res_allowed]) == res_allowed:
                    return True, "allowed_directory"
            except (ValueError, Exception):
                pass

        for approved in self.session_approved_dirs:
            try:
                if os.path.commonpath([resolved, approved]) == approved:
                    return True, "session_approved"
            except (ValueError, Exception):
                pass

        action_name = "WRITE" if is_write else "READ"
        print("\n" + "=" * 70)
        print(f"[SECURITY ALERT: External Directory Access Requested]")
        print(f"Action:           {action_name}")
        print(f"Target Path:      {resolved}")
        print(f"Active Workspace: {self.workspace_root}")
        print("=" * 70)
        print("Authorize this action?")
        print("  [y] Yes (this time only)")
        print("  [a] Always (authorize this directory for remainder of session)")
        print("  [n] No (deny access)")

        if prompt_callback:
            choice = prompt_callback(resolved, action_name)
        else:
            try:
                choice = input("Your choice [y/n/a]: ").strip().lower()
            except (KeyboardInterrupt, EOFError):
                choice = "n"

        if choice in ["y", "yes"]:
            return True, "user_approved_once"
        elif choice in ["a", "always"]:
            target_dir = os.path.dirname(resolved) if not os.path.isdir(resolved) else resolved
            self.session_approved_dirs.add(target_dir)
            print(f"[Security] Directory '{target_dir}' approved for this session.")
            return True, "user_approved_always"
        else:
            return False, f"Permission denied by user. Access to external path '{resolved}' was not authorized."

    def check_command_access(self, command: str, prompt_callback=None) -> Tuple[bool, str]:
        """
        Inspects shell command for external path references or directory traversals.
        Returns (is_allowed, reason_or_error_message).
        """
        perms = self.settings.get("permissions", {})
        auto_approve = perms.get("auto_approve_external", False)

        if not perms.get("require_hitl_for_external_access", True) or auto_approve:
            return True, "settings_override"

        has_traversal = ".." in command
        abs_path_match = re.search(r"[A-Za-z]:[\\/][^ \t\n\r\"']+", command)

        if has_traversal or abs_path_match:
            if abs_path_match:
                path_ref = abs_path_match.group(0)
                if self.is_within_workspace(path_ref):
                    return True, "within_workspace"

                resolved_path = os.path.realpath(os.path.abspath(path_ref))
                for allowed in perms.get("allowed_directories", []):
                    try:
                        res_allowed = os.path.realpath(os.path.abspath(allowed))
                        if os.path.commonpath([resolved_path, res_allowed]) == res_allowed:
                            return True, "allowed_directory"
                    except (ValueError, Exception):
                        pass

                for approved in self.session_approved_dirs:
                    try:
                        if os.path.commonpath([resolved_path, approved]) == approved:
                            return True, "session_approved"
                    except (ValueError, Exception):
                        pass

            print("\n" + "=" * 70)
            print(f"[SECURITY ALERT: External Shell Command Execution Requested]")
            print(f"Command:          {command}")
            print(f"Active Workspace: {self.workspace_root}")
            print("=" * 70)
            print("Authorize this command execution?")
            print("  [y] Yes (run command)")
            print("  [n] No (abort)")

            if prompt_callback:
                choice = prompt_callback(command, "COMMAND")
            else:
                try:
                    choice = input("Your choice [y/n]: ").strip().lower()
                except (KeyboardInterrupt, EOFError):
                    choice = "n"

            if choice in ["y", "yes"]:
                return True, "user_approved_command"
            else:
                return False, f"Permission denied by user. Execution of command with external paths was aborted."

        return True, "clean_command"
