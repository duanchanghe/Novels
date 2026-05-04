# ===========================================
# Storage Configuration (MinIO/S3)
# ===========================================

"""
MinIO object storage configuration for EPUB files and audio.
"""

import os

# Connection
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() in ("true", "1", "yes")

# Buckets
MINIO_BUCKET_EPUB = os.getenv("MINIO_BUCKET_EPUB", "books-epub")
MINIO_BUCKET_AUDIO = os.getenv("MINIO_BUCKET_AUDIO", "books-audio")

# Bucket configuration
MINIO_BUCKETS_CONFIG = {
    MINIO_BUCKET_EPUB: {
        "policy": "private",
        "lifecycle_days": 90,  # Auto-delete after 90 days
    },
    MINIO_BUCKET_AUDIO: {
        "policy": "private",
        "lifecycle_days": 365,  # Keep audio longer
    },
}

# Upload settings
MINIO_UPLOAD_CHUNK_SIZE = 10 * 1024 * 1024  # 10MB
MINIO_UPLOAD_MAX_SIZE = 500 * 1024 * 1024  # 500MB

# URL expiration (for presigned URLs)
MINIO_PRESIGNED_URL_EXPIRY = 3600  # 1 hour
