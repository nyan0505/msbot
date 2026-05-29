import os
from dotenv import load_dotenv

load_dotenv()

APP_ID: str = os.environ.get("MicrosoftAppId", "")
APP_SECRET: str = os.environ.get("MicrosoftAppPassword", "")
APP_TYPE: str = os.environ.get("MicrosoftAppType", "")
TENANT_ID: str = os.environ.get("AZURE_TENANT_ID", "")

LITELLM_BASE_URL: str = os.environ.get("LITELLM_BASE_URL", "")
BEARER_TOKEN: str = os.environ.get("BEARER_TOKEN", "")
LITELLM_API_KEY: str = os.environ.get("LITELLM_API_KEY", os.environ.get("BEARER_TOKEN", ""))
LITELLM_MODEL: str = os.environ.get("LITELLM_MODEL", "openai/gpt-4o-mini")
LLM_TIMEOUT: int = int(os.environ.get("LLM_TIMEOUT", "30"))

SEARCH_TOP_K: int = int(os.environ.get("SEARCH_TOP_K", "5"))
SEARCH_TIMEOUT: int = int(os.environ.get("SEARCH_TIMEOUT", "15"))
