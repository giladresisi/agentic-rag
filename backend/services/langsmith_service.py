import os
from config import settings

def setup_langsmith():
    """
    Configure LangSmith environment variables for tracing.

    Note: LangSmith is optional. If not configured, tracing will be disabled.
    """
    try:
        os.environ["LANGCHAIN_TRACING_V2"] = str(settings.LANGSMITH_TRACING).lower()
        os.environ["LANGCHAIN_API_KEY"] = settings.LANGSMITH_API_KEY
        os.environ["LANGCHAIN_PROJECT"] = settings.LANGSMITH_PROJECT
        print("✓ LangSmith tracing enabled")
    except Exception as e:
        print(f"⚠ LangSmith not configured (optional): {e}")
        # Disable tracing if configuration fails
        os.environ["LANGCHAIN_TRACING_V2"] = "false"

# Initialize on import
setup_langsmith()
