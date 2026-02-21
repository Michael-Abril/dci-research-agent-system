"""
Streamlit Cloud entry point.
Redirects to the main application in app/main.py
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Import and run the main app
from app.main import *
