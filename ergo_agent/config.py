import os
from dotenv import load_dotenv

# Load .env file (only for local dev; production uses real env vars)
load_dotenv()

# Read secrets from environment
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY")

# Read and parse API keys
API_KEYS_STR = os.getenv("API_KEYS", "")
VALID_API_KEYS = {key.strip() for key in API_KEYS_STR.split(",") if key.strip()}

# Validate required secrets
if not ANTHROPIC_API_KEY:
    raise RuntimeError(
        "ANTHROPIC_API_KEY is not set. "
        "Copy .env.example to .env and add your API key."
    )

if not LANGCHAIN_API_KEY:
    raise RuntimeError(
        "LANGCHAIN_API_KEY is not set. "
        "Copy .env.example to .env and add your API key."
    )

if not VALID_API_KEYS:
    raise RuntimeError(
        "No API keys configured. "
        "Set API_KEYS in .env to a comma-separated list of valid keys."
    )

# Set environment variables for downstream libraries
os.environ["ANTHROPIC_API_KEY"] = ANTHROPIC_API_KEY
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "ergonomic-risk-assessment"
os.environ["LANGCHAIN_API_KEY"] = LANGCHAIN_API_KEY
