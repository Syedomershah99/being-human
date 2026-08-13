#!/usr/bin/env python3
"""Shim kept so existing MCP client configs keep working. Real code lives in
being_human/server.py -- edit that, not this."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from being_human.server import main

if __name__ == "__main__":
    sys.exit(main())
