#!/usr/bin/env python3
"""
MQTT User Management for Skytrack Backend.
Creates or updates MQTT users with open-all role using mosquitto_ctrl.
"""

import os
import shutil
import subprocess
import sys
from typing import List


def _run(cmd: List[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run a command and print full diagnostics."""
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    print(f"CMD: {' '.join(cmd)}")
    print(f"RET: {result.returncode}")
    if result.stdout:
        print(f"STDOUT: {result.stdout.strip()}")
    if result.stderr:
        print(f"STDERR: {result.stderr.strip()}")
    if check and result.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}")
    return result


def _tool_exists(name: str) -> bool:
    return shutil.which(name) is not None


def _safe_run_dynsec(base_cmd: List[str], args: List[str], ignore_errors: List[str] = None) -> bool:
    """Run a dynsec command and optionally ignore known benign errors."""
    ignore_errors = ignore_errors or []
    result = _run(base_cmd + args, check=False)
    if result.returncode == 0:
        return True

    stderr = (result.stderr or "").lower()
    for err in ignore_errors:
        if err.lower() in stderr:
            return True
    return False


def create_mqtt_user(username: str, password: str) -> bool:
    ca_file = os.getenv("MQTT_CA_FILE", "/home/azureuser/Skytrack_Backend/Skytronsystem/keys/ca.crt")
    host = os.getenv("MQTT_BROKER_HOST", "103.195.217.127")
    port = os.getenv("MQTT_BROKER_PORT", "8883")
    admin_user = os.getenv("MQTT_ADMIN_USER", "admin")
    admin_pass = os.getenv("MQTT_ADMIN_PASS", "adminpass")

    username = (username or "").strip()
    password = (password or "").strip()

    if not username:
        print("ERROR: username is empty. Provide arg1 or export MQTT_USERNAME.")
        return False
    if not password:
        print("ERROR: password is empty. Provide arg2 or export MQTT_PASSWORD.")
        return False

    if not _tool_exists("mosquitto_ctrl"):
        print("ERROR: mosquitto_ctrl not found in PATH")
        return False
    if not _tool_exists("mosquitto_pub"):
        print("ERROR: mosquitto_pub not found in PATH")
        return False
    if not os.path.exists(ca_file):
        print(f"ERROR: CA file not found at {ca_file}")
        return False

    print("=== MQTT TARGET ===")
    print(f"HOST={host}")
    print(f"PORT={port}")
    print(f"CA_FILE={ca_file}")
    print(f"ADMIN_USER={admin_user}")
    print(f"USERNAME={username}")

    base_ctrl = [
        "mosquitto_ctrl", "--cafile", ca_file,
        "-h", host, "-p", port,
        "-u", admin_user, "-P", admin_pass,
        "dynsec",
    ]

    try:
        # Ensure role exists
        _safe_run_dynsec(
            base_ctrl,
            ["createRole", "open-all"],
            ignore_errors=["already", "exists"],
        )

        # Ensure broad ACLs exist on role
        acl_specs = [
            ["addRoleACL", "open-all", "publishClientSend", "#", "allow"],
            ["addRoleACL", "open-all", "publishClientReceive", "#", "allow"],
            ["addRoleACL", "open-all", "subscribePattern", "#", "allow"],
            ["addRoleACL", "open-all", "unsubscribePattern", "#", "allow"],
        ]
        for spec in acl_specs:
            _safe_run_dynsec(base_ctrl, spec, ignore_errors=["already", "exists"]) 

        # Create client if missing, then set password always
        _safe_run_dynsec(
            base_ctrl,
            ["createClient", username, "-p", password],
            ignore_errors=["already", "exists"],
        )
        _run(base_ctrl + ["setClientPassword", username, password], check=True)

        # Attach role and enable user
        _safe_run_dynsec(base_ctrl, ["addClientRole", username, "open-all"], ignore_errors=["already", "exists"])
        _safe_run_dynsec(base_ctrl, ["enableClient", username], ignore_errors=["already", "enabled"])

        # Show client details for debug
        _run(base_ctrl + ["getClient", username], check=False)

        # Final auth test as the created user
        test_cmd = [
            "mosquitto_pub", "-d",
            "--cafile", ca_file,
            "-h", host, "-p", port,
            "-u", username, "-P", password,
            "-t", f"test/{username}",
            "-m", f"user-create-check:{username}",
            "-q", "1",
        ]
        test = _run(test_cmd, check=False)
        if test.returncode == 0:
            print(f"SUCCESS: User '{username}' can authenticate and publish.")
            return True

        print("ERROR: User creation commands ran, but login test failed.")
        print("This usually means broker is using go-auth/JWT mode, not dynsec for user auth.")
        return False

    except Exception as exc:
        print(f"ERROR: Exception in create_mqtt_user: {exc}")
        return False


if __name__ == "__main__":
    arg_user = sys.argv[1] if len(sys.argv) > 1 else os.getenv("MQTT_USERNAME", "")
    arg_pass = sys.argv[2] if len(sys.argv) > 2 else os.getenv("MQTT_PASSWORD", "")

    print(f"Creating/updating MQTT user: '{arg_user}'")
    success = create_mqtt_user(arg_user, arg_pass)
    if success:
        print(f"OK: User '{arg_user}' created/updated successfully.")
        sys.exit(0)

    print(f"FAIL: Could not create/update user '{arg_user}'.")
    sys.exit(1)
