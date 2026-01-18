#!/usr/bin/env python3
"""Auto-start a bot when the server launches."""
import sys
import time
from pathlib import Path

import requests

GREEN = "\033[0;32m"
BLUE = "\033[0;34m"
YELLOW = "\033[1;33m"
RED = "\033[0;31m"
NC = "\033[0m"

BASE_URL = "http://localhost:8020"


def load_config() -> tuple[str | None, str | None, str | None]:
    env_file = Path(".env.dev")
    if not env_file.exists():
        return None, None, None

    config = {}
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            config[key.strip()] = value.strip()

    return (
        config.get("DEV_EMAIL"),
        config.get("DEV_PASSWORD"),
        config.get("AUTO_START_BOT_ID"),
    )


def wait_for_server(timeout: int = 30) -> bool:
    print(f"{BLUE}Waiting for server...{NC}")
    start = time.time()

    while time.time() - start < timeout:
        try:
            if requests.get(f"{BASE_URL}/health", timeout=2).status_code == 200:
                print(f"{GREEN}Server ready{NC}")
                return True
        except requests.RequestException:
            pass
        print(".", end="", flush=True)
        time.sleep(1)

    print(f"\n{RED}Server timeout{NC}")
    return False


def get_token(email: str, password: str) -> str | None:
    print(f"{BLUE}Authenticating...{NC}")
    try:
        resp = requests.post(
            f"{BASE_URL}/auth/login",
            json={"email": email, "password": password},
            timeout=5,
        )
        if resp.status_code == 200:
            print(f"{GREEN}Authenticated{NC}")
            return resp.json().get("token")
        print(f"{RED}Auth failed: {resp.status_code}{NC}")
    except requests.RequestException as e:
        print(f"{RED}Error: {e}{NC}")
    return None


def get_last_usable_bot(token: str) -> str | None:
    print(f"{BLUE}Finding usable bot...{NC}")
    try:
        resp = requests.get(
            f"{BASE_URL}/api/bots",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5,
        )
        if resp.status_code != 200:
            print(f"{RED}Failed to list bots: {resp.status_code}{NC}")
            return None

        data = resp.json()
        bots = data.get("bots", []) if isinstance(data, dict) else data

        usable = [b for b in bots if b["status"] != "stopped"]
        if not usable:
            print(f"{YELLOW}No usable bots found{NC}")
            return None

        bot = usable[-1]
        print(f"{GREEN}Found: {bot['name']} ({bot['id']}){NC}")
        return bot["id"]

    except requests.RequestException as e:
        print(f"{RED}Error: {e}{NC}")
        return None


def start_bot(bot_id: str, token: str) -> bool:
    print(f"{BLUE}Starting bot {bot_id}...{NC}")
    try:
        resp = requests.post(
            f"{BASE_URL}/api/bots/{bot_id}/start",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json() if resp.text else {}
            details = data.get("details") if isinstance(data, dict) else None
            status = (details.get("status") if details else None) or data.get(
                "status", "started"
            )
            print(f"{GREEN}Bot started - Status: {status}{NC}")
            return True

        print(f"{RED}Failed: {resp.status_code}{NC}")
        try:
            print(f"{RED}  {resp.json().get('detail', resp.text)}{NC}")
        except ValueError:
            print(f"{RED}  {resp.text}{NC}")

    except requests.RequestException as e:
        print(f"{RED}Error: {e}{NC}")
    return False


def main():
    print(f"\n{BLUE}{'=' * 40}{NC}")
    print(f"{BLUE}Auto-Start Bot{NC}")
    print(f"{BLUE}{'=' * 40}{NC}\n")

    email, password, auto_bot_id = load_config()

    if not email or not password:
        print(f"{RED}Missing credentials in .env.dev{NC}")
        print("Required: DEV_EMAIL, DEV_PASSWORD")
        sys.exit(1)

    # Priority: CLI arg > .env.dev > auto-detect
    bot_id = sys.argv[1] if len(sys.argv) > 1 else auto_bot_id
    if bot_id:
        print(f"{BLUE}Bot ID: {bot_id}{NC}\n")

    if not wait_for_server():
        sys.exit(1)

    token = get_token(email, password)
    if not token:
        sys.exit(1)

    if not bot_id:
        bot_id = get_last_usable_bot(token)
        if not bot_id:
            print(f"{YELLOW}Create a bot first{NC}")
            sys.exit(1)

    if start_bot(bot_id, token):
        print(f"\n{GREEN}Bot running - check server logs{NC}")
        sys.exit(0)
    sys.exit(1)


if __name__ == "__main__":
    main()
