from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from services.supabase_service import get_supabase

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> dict:
    """
    Validate JWT token and return current user.

    Raises:
        HTTPException: If token is invalid or expired.
    """
    token = credentials.credentials
    supabase = get_supabase()

    try:
        # Verify token with Supabase
        user_response = supabase.auth.get_user(token)

        if not user_response or not user_response.user:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")

        return {
            "id": user_response.user.id,
            "email": user_response.user.email,
            "token": token
        }

    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
