"""
pytest configuration for backend tests.
Ensures backend modules can be imported when running tests from the tests directory.
"""
import sys
from pathlib import Path

# Add backend directory to Python path so tests can import backend modules
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))
