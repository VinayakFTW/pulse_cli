import os
import sys
import json
import tempfile
import shutil

# Ensure UTF-8 output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Ensure project root in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pulse_tools.permission_manager import PermissionManager
from pulse_tools.general_tools import write_file, read_file, set_workspace_root, get_permission_manager


def test_permission_guardrail_suite():
    print("--- Starting Permission Guardrail Test Suite ---")

    # Set up dummy workspace and external test directory
    temp_workspace = tempfile.mkdtemp(prefix="pulse_ws_test_")
    temp_external = tempfile.mkdtemp(prefix="pulse_ext_test_")

    try:
        pm = PermissionManager(workspace_root=temp_workspace)

        # 1. Inside workspace path
        print("[1] Testing inside-workspace path...")
        in_path = os.path.join(temp_workspace, "inside.txt")
        allowed, reason = pm.check_path_access(in_path, is_write=True)
        assert allowed is True, f"Expected allowed, got {allowed}"
        assert reason == "within_workspace"
        print("    PASSED: Within-workspace access allowed with 0 prompts.")

        # 2. Outside workspace with denial
        print("[2] Testing external path with user denial (n)...")
        ext_path = os.path.join(temp_external, "ext_secret.txt")
        allowed, reason = pm.check_path_access(ext_path, is_write=True, prompt_callback=lambda p, a: "n")
        assert allowed is False, f"Expected denied, got {allowed}"
        assert "Permission denied by user" in reason
        print("    PASSED: External path correctly denied upon 'n'.")

        # 3. Outside workspace with single approval
        print("[3] Testing external path with user approval (y)...")
        allowed, reason = pm.check_path_access(ext_path, is_write=True, prompt_callback=lambda p, a: "y")
        assert allowed is True, f"Expected approved, got {allowed}"
        assert reason == "user_approved_once"
        print("    PASSED: External path allowed once upon 'y'.")

        # 4. Outside workspace with session approval (always)
        print("[4] Testing external path with session approval (always)...")
        ext_file1 = os.path.join(temp_external, "sub", "file1.txt")
        ext_file2 = os.path.join(temp_external, "sub", "file2.txt")
        allowed, reason = pm.check_path_access(ext_file1, is_write=True, prompt_callback=lambda p, a: "a")
        assert allowed is True and reason == "user_approved_always"
        
        # Second access should be auto-approved without triggering callback
        called = False
        def should_not_be_called(p, a):
            nonlocal called
            called = True
            return "n"
        allowed2, reason2 = pm.check_path_access(ext_file2, is_write=True, prompt_callback=should_not_be_called)
        assert allowed2 is True, f"Expected session approved, got {allowed2}"
        assert reason2 == "session_approved"
        assert not called, "Prompt callback should not have been called for session-approved folder"
        print("    PASSED: Session approval 'always' works without re-prompting.")

        # 5. Testing pulse_settings.json overrides: allowed_directories
        print("[5] Testing pulse_settings.json allowed_directories...")
        settings_file = os.path.join(temp_workspace, "pulse_settings.json")
        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump({
                "permissions": {
                    "allowed_directories": [temp_external],
                    "require_hitl_for_external_access": True
                }
            }, f)

        pm_with_settings = PermissionManager(workspace_root=temp_workspace)
        test_file = os.path.join(temp_external, "any_file.txt")
        allowed, reason = pm_with_settings.check_path_access(test_file, is_write=True)
        assert allowed is True, f"Expected allowed by settings, got {allowed}"
        assert reason == "allowed_directory"
        print("    PASSED: allowed_directories in pulse_settings.json auto-approved.")

        # 6. Testing pulse_settings.json overrides: require_hitl_for_external_access = false
        print("[6] Testing require_hitl_for_external_access = false...")
        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump({
                "permissions": {
                    "allowed_directories": [],
                    "require_hitl_for_external_access": False
                }
            }, f)

        pm_bypass = PermissionManager(workspace_root=temp_workspace)
        allowed, reason = pm_bypass.check_path_access(os.path.join(temp_external, "bypass.txt"), is_write=True)
        assert allowed is True, f"Expected settings override, got {allowed}"
        assert reason == "settings_override"
        print("    PASSED: require_hitl_for_external_access=false bypasses HITL.")

        # 7. Testing general_tools integration
        print("[7] Testing write_file and read_file tools with PermissionManager...")
        # Reset settings file to require HITL
        if os.path.exists(settings_file):
            os.remove(settings_file)

        set_workspace_root(temp_workspace)
        tool_pm = get_permission_manager()

        # Mock input denial for external file write
        orig_input = __builtins__.input if hasattr(__builtins__, "input") else input
        import builtins
        builtins.input = lambda prompt="": "n"
        try:
            res = write_file(os.path.join(temp_external, "denied.txt"), "hello")
            assert "Permission denied" in res or "Error" in res, f"Expected denial error, got: {res}"
            print("    PASSED: general_tools write_file blocks unauthorized external writes.")
        finally:
            builtins.input = orig_input


        # Write inside workspace succeeds
        res_in = write_file("local_test.txt", "hello local")
        assert "written successfully" in res_in
        assert os.path.exists(os.path.join(temp_workspace, "local_test.txt"))
        read_content = read_file("local_test.txt")
        assert read_content == "hello local"
        print("    PASSED: general_tools write_file and read_file operate freely within workspace.")

        print("\nALL PERMISSION GUARDRAIL TESTS PASSED SUCCESSFULLY!")

    finally:
        shutil.rmtree(temp_workspace, ignore_errors=True)
        shutil.rmtree(temp_external, ignore_errors=True)


if __name__ == "__main__":
    test_permission_guardrail_suite()
