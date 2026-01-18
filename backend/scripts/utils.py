#!/usr/bin/env python3
"""Shared utilities for backend scripts."""
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from src.core.database import AsyncSessionLocal

# Terminal colors
GREEN = "\033[0;32m"
BLUE = "\033[0;34m"
YELLOW = "\033[1;33m"
RED = "\033[0;31m"
NC = "\033[0m"


class DBSession:
    """Async database session context manager."""

    async def __aenter__(self):
        self._session = AsyncSessionLocal()
        return self._session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self._session.rollback()
        await self._session.close()


def get_project_root() -> Path:
    return Path(__file__).parent.parent.parent


def get_env_file() -> Path:
    return get_project_root() / ".env.dev"


def update_env_var(key: str, value: str) -> bool:
    """Update or add an environment variable in .env.dev."""
    env_file = get_env_file()

    try:
        if env_file.exists():
            lines = env_file.read_text().splitlines(keepends=True)
            found = False
            for i, line in enumerate(lines):
                if line.strip().startswith(f"{key}="):
                    lines[i] = f"{key}={value}\n"
                    found = True
                    break

            if not found:
                if lines and not lines[-1].endswith("\n"):
                    lines.append("\n")
                lines.append(f"\n{key}={value}\n")

            env_file.write_text("".join(lines))
        else:
            env_file.write_text(
                f"# Configuration\n{key}={value}\n"
            )
        return True
    except Exception as e:
        print(f"{YELLOW}Could not save {key} to .env.dev: {e}{NC}")
        return False


def print_header(title: str) -> None:
    print(f"\n{BLUE}{'=' * 50}{NC}")
    print(f"{BLUE}{title}{NC}")
    print(f"{BLUE}{'=' * 50}{NC}\n")


def print_bot_info(bot, detailed: bool = False) -> None:
    print(f"  ID: {bot.id}")
    print(f"  Name: {bot.name}")
    print(f"  Status: {bot.status}")
    print(f"  Capital: ${bot.capital:,.2f}")
    if detailed and hasattr(bot, "initial_capital"):
        print(f"  Initial: ${bot.initial_capital:,.2f}")
    if detailed and hasattr(bot, "risk_params"):
        print(f"  Risk Params: {bot.risk_params}")
