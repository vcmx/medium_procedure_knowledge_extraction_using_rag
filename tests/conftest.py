"""
Test configuration and fixtures.
"""

import os
import sys
from pathlib import Path

# Add the project root directory to the Python path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))


# Create necessary directories if they don't exist
os.makedirs(ROOT_DIR / "input-pdfs", exist_ok=True)
os.makedirs(ROOT_DIR / "processed_output", exist_ok=True)
os.makedirs(ROOT_DIR / "test_output", exist_ok=True)


def pytest_configure(config):
    """Register custom marks."""
    config.addinivalue_line(
        "markers", "timeout: mark test to timeout after specified seconds"
    )
