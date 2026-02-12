import os
from config import settings

def setup_langsmith():
    """
    Configure LangSmith environment variables for tracing.

    Note: LangSmith is optional. If not configured, tracing will be disabled.
    """
    try:
        # Check if API key is configured
        if not settings.LANGSMITH_API_KEY:
            print("[WARNING] LangSmith API key not set - tracing disabled")
            os.environ["LANGCHAIN_TRACING_V2"] = "false"
            return

        # Set environment variables
        os.environ["LANGCHAIN_TRACING_V2"] = str(settings.LANGSMITH_TRACING).lower()
        os.environ["LANGCHAIN_API_KEY"] = settings.LANGSMITH_API_KEY
        os.environ["LANGCHAIN_PROJECT"] = settings.LANGSMITH_PROJECT
        os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"

        print(f"[OK] LangSmith tracing enabled (project: {settings.LANGSMITH_PROJECT})")
    except Exception as e:
        print(f"[WARNING] LangSmith configuration failed: {e}")
        os.environ["LANGCHAIN_TRACING_V2"] = "false"

# Initialize on import
setup_langsmith()
