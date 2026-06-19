#!/usr/bin/env python3
"""
Grocery Tycoon -- entry point.

Just run:   python3 main.py
(or double-click "Play Grocery Tycoon.command" in Finder)

On the very first run this auto-creates a local virtual environment and
installs pygame, then relaunches itself. No manual setup needed.
"""
import os
import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
VENV_PY = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _have_pygame():
    try:
        import pygame  # noqa: F401
        return True
    except Exception:
        return False


def _bootstrap():
    """Create a local venv + install pygame, then re-exec inside it."""
    if not VENV_PY.exists():
        print("First-time setup: creating a local environment...")
        subprocess.run([sys.executable, "-m", "venv", str(VENV)], check=True)
    print("Installing pygame (one-time, needs internet)...")
    subprocess.run([str(VENV_PY), "-m", "pip", "install", "--quiet",
                    "--upgrade", "pip"])
    subprocess.run([str(VENV_PY), "-m", "pip", "install", "--quiet", "pygame"],
                   check=True)
    env = dict(os.environ, GROCERY_BOOTSTRAPPED="1")
    os.execve(str(VENV_PY), [str(VENV_PY), str(ROOT / "main.py")], env)


def main():
    if not _have_pygame():
        if os.environ.get("GROCERY_BOOTSTRAPPED"):
            sys.exit("Could not load pygame even after setup.\n"
                     "Try manually:  python3 -m pip install pygame")
        try:
            _bootstrap()           # this re-execs and does not return
        except subprocess.CalledProcessError:
            sys.exit("Setup failed. Make sure you have internet, then run:\n"
                     "  python3 -m pip install pygame  &&  python3 main.py")
    print("Launching Grocery Tycoon...")
    from game import Game
    Game().run()


if __name__ == "__main__":
    main()
