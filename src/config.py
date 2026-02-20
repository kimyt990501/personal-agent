import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "conversations.db"

# Discord
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# Ollama
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")

# Conversation
MAX_HISTORY_LENGTH = int(os.getenv("MAX_HISTORY_LENGTH", "20"))

# Context Compression
SUMMARY_THRESHOLD = int(os.getenv("SUMMARY_THRESHOLD", "20"))
SUMMARY_KEEP_RECENT = int(os.getenv("SUMMARY_KEEP_RECENT", "10"))

# Email
EMAIL_NAVER_USER = os.getenv("EMAIL_NAVER_USER", "")
EMAIL_NAVER_PASSWORD = os.getenv("EMAIL_NAVER_PASSWORD", "")
EMAIL_GMAIL_USER = os.getenv("EMAIL_GMAIL_USER", "")
EMAIL_GMAIL_PASSWORD = os.getenv("EMAIL_GMAIL_PASSWORD", "")
EMAIL_DEFAULT_PROVIDER = os.getenv("EMAIL_DEFAULT_PROVIDER", "naver")
