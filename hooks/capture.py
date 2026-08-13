#!/usr/bin/env python3
"""Shim kept so the UserPromptSubmit hook config keeps working. Real code lives
in being_human/capture.py -- edit that, not this."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from being_human.capture import main
except Exception:
    sys.exit(0)   # a voice tool must never block a prompt

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
