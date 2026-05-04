# ===========================================
# File Watcher Configuration
# ===========================================

"""
Configuration for EPUB file watching and processing.
"""

import os

# Watch directories
WATCH_DIR = os.getenv("WATCH_DIR", "/books/incoming")
WATCH_DIRS = os.getenv("WATCH_DIRS", "")

# Parse additional watch directories
def get_watch_dirs():
    dirs = [WATCH_DIR]
    if WATCH_DIRS:
        dirs.extend([d.strip() for d in WATCH_DIRS.split(",") if d.strip()])
    return dirs

# Watch settings
WATCH_INTERVAL = int(os.getenv("WATCH_INTERVAL", "60"))  # seconds
WATCH_ENABLED = os.getenv("WATCH_ENABLED", "true").lower() in ("true", "1", "yes")
WATCH_CONCURRENT = int(os.getenv("WATCH_CONCURRENT", "3"))  # Max concurrent tasks
WATCH_MAX_FILE_SIZE_MB = int(os.getenv("WATCH_MAX_FILE_SIZE_MB", "500"))
WATCH_STATUS_INTERVAL = int(os.getenv("WATCH_STATUS_INTERVAL", "300"))  # seconds

# Dead letter queue
WATCH_DEAD_LETTER_DIR = os.getenv("WATCH_DEAD_LETTER_DIR", "/books/dead-letter")

# File patterns
WATCH_FILE_EXTENSIONS = [".epub", ".EPUB"]
WATCH_EXCLUDE_PATTERNS = [".~", ".tmp", ".DS_Store", "Thumbs.db"]

# Processing settings
WATCH_BATCH_SIZE = 5  # Files to process per batch
WATCH_POLL_TIMEOUT = 30  # Timeout for file system events
