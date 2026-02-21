"""
pytest configuration for backend tests.
Ensures backend modules and test utilities can be imported when running tests.
"""
import sys
from pathlib import Path

# Add backend directory to Python path so tests can import backend modules
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Add tests directory so test_utils can be imported by tests in subdirectories
tests_dir = Path(__file__).parent
if str(tests_dir) not in sys.path:
    sys.path.insert(0, str(tests_dir))
