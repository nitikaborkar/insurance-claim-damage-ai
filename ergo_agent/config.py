import os

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY")

if not ANTHROPIC_API_KEY:
    raise RuntimeError("ANTHROPIC_API_KEY is not set")

os.environ["ANTHROPIC_API_KEY"] = ANTHROPIC_API_KEY
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "ergonomic-risk-assessment"
os.environ["LANGCHAIN_API_KEY"] = LANGCHAIN_API_KEY if LANGCHAIN_API_KEY else ""