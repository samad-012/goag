import hashlib
import hmac

from fastapi import HTTPException, status

from .config import get_settings


def hash_device_id(device_id: str) -> str:
    settings = get_settings()
    secret = settings.device_hash_secret or settings.supabase_jwt_secret
    if not secret:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Device hashing is not configured")
    return hmac.new(secret.encode(), device_id.encode(), hashlib.sha256).hexdigest()

