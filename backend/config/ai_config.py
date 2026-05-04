# ===========================================
# AI API Configuration
# ===========================================

"""
Configuration for AI services: DeepSeek and MiniMax.
"""

import os

# ===========================================
# DeepSeek API (Text Analysis)
# ===========================================

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_MAX_TOKENS = int(os.getenv("DEEPSEEK_MAX_TOKENS", "4096"))
DEEPSEEK_TEMPERATURE = float(os.getenv("DEEPSEEK_TEMPERATURE", "0.7"))

# DeepSeek Request Settings
DEEPSEEK_REQUEST_TIMEOUT = 60  # seconds
DEEPSEEK_MAX_RETRIES = 3
DEEPSEEK_RETRY_DELAY = 2  # seconds

# DeepSeek Batch Processing
DEEPSEEK_BATCH_SIZE = 10  # Chapters per batch for analysis

# ===========================================
# MiniMax TTS API (Text-to-Speech)
# ===========================================

MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY", "")
MINIMAX_API_HOST = os.getenv("MINIMAX_API_HOST", "https://api.minimax.chat")
MINIMAX_GROUP_ID = os.getenv("MINIMAX_GROUP_ID", "")

# MiniMax TTS Settings
MINIMAX_TTS_VOICE = os.getenv("MINIMAX_TTS_VOICE", "female-tianmei")
MINIMAX_TTS_SPEED = float(os.getenv("MINIMAX_TTS_SPEED", "1.0"))
MINIMAX_TTS_PITCH = float(os.getenv("MINIMAX_TTS_PITCH", "0"))
MINIMAX_TTS_VOLUME = float(os.getenv("MINIMAX_TTS_VOLUME", "0"))
MINIMAX_TTS_FORMAT = "mp3"
MINIMAX_TTS_BITRATE = "192k"
MINIMAX_TTS_SAMPLE_RATE = 44100

# MiniMax API Settings
MINIMAX_REQUEST_TIMEOUT = 120  # seconds
MINIMAX_MAX_RETRIES = 2
MINIMAX_RETRY_DELAY = 5  # seconds

# ===========================================
# Cost Control
# ===========================================

COST_DAILY_LIMIT = float(os.getenv("COST_DAILY_LIMIT", "50"))
COST_WARNING_THRESHOLD = 0.8  # Alert at 80% of daily limit

# Estimated costs (for tracking)
COST_DEEPSEEK_PER_1K_TOKENS = 0.001  # USD
COST_MINIMAX_PER_1K_CHARS = 0.0001  # USD
