# ===========================================
# Audio Processing Configuration
# ===========================================

"""
Configuration for audio post-processing and encoding.
"""

import os

# Audio encoding
AUDIO_SAMPLE_RATE = int(os.getenv("AUDIO_SAMPLE_RATE", "44100"))
AUDIO_BITRATE = int(os.getenv("AUDIO_BITRATE", "192"))  # kbps
AUDIO_CHANNELS = 2  # stereo
AUDIO_FORMAT = "mp3"

# Crossfade for chapter transitions
AUDIO_CROSSFADE_MS = int(os.getenv("AUDIO_CROSSFADE_MS", "20"))

# Normalization
AUDIO_NORMALIZE = os.getenv("AUDIO_NORMALIZE", "true").lower() in ("true", "1", "yes")
AUDIO_NORMALIZE_LEVEL = float(os.getenv("AUDIO_NORMALIZE_LEVEL", "-20"))  # dB

# Silence detection
AUDIO_SILENCE_THRESHOLD = int(os.getenv("AUDIO_SILENCE_THRESHOLD", "-40"))  # dB
AUDIO_MIN_SILENCE_DURATION = 0.5  # seconds

# ID3 Tags
AUDIO_ID3_VERSION = "id3v2.4"
AUDIO_EMBED_COVER = True

# Processing limits
AUDIO_MAX_DURATION = 3600 * 4  # 4 hours max per file
AUDIO_MIN_DURATION = 1  # second
