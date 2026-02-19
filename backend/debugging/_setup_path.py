"""
Path setup for debugging scripts.
Import this at the top of debugging scripts to enable backend module imports.
"""
import sys
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))
