"""
tests/conftest.py
Configures pytest environment and adds root directory to sys.path.
"""

import os
import sys

# Add repository root to sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
