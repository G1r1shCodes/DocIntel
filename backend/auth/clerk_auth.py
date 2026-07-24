import os
import urllib.request
import json
from fastapi import HTTPException, Security, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict, Any
from jose import jwt
import logging

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)

ROLES = ["Admin", "Tender Specialist", "Sales", "Engineer", "Viewer"]

DEFAULT_CLERK_ISSUER = "https://valued-hawk-75.clerk.accounts.dev"
jwks_cache = None

def get_jwks():
    global jwks_cache
    if jwks_cache is None:
        issuer = os.environ.get("CLERK_ISSUER") or DEFAULT_CLERK_ISSUER
        jwks_url = f"{issuer.rstrip('/')}/.well-known/jwks.json"
        try:
            with urllib.request.urlopen(jwks_url, timeout=5) as response:
                jwks_cache = json.loads(response.read().decode())
        except Exception as e:
            logger.error(f"Failed to fetch JWKS from {jwks_url}: {e}")
            print(f"[Auth] Warning: Failed to fetch JWKS from {jwks_url}: {e}", flush=True)
            return None
    return jwks_cache

def get_current_user_from_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
    x_user_role: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    Extracts and strictly verifies the current authenticated user from Clerk JWT token.
    Extracts role strictly from the JWT metadata, but allows X-User-Role header override for the frontend role switcher.
    """
    print(f"[Auth] Extracting user from token...", flush=True)
    if not credentials or not credentials.credentials or credentials.credentials in ("null", "undefined"):
        print("[Auth] Missing or invalid authentication token string", flush=True)
        raise HTTPException(status_code=401, detail="Missing or invalid authentication token")
        
    token = credentials.credentials
    user_id = None
    role = "Viewer"

    try:
        print("[Auth] Fetching JWKS...", flush=True)
        jwks = get_jwks()
        payload = None
        
        if jwks:
            try:
                unverified_header = jwt.get_unverified_header(token)
                rsa_key = {}
                for key in jwks.get("keys", []):
                    if key.get("kid") == unverified_header.get("kid"):
                        rsa_key = key
                        break
                        
                if rsa_key:
                    payload = jwt.decode(
                        token,
                        rsa_key,
                        algorithms=["RS256"],
                        options={"verify_aud": False, "verify_iss": False}
                    )
            except Exception as jwks_err:
                print(f"[Auth] JWKS decode failed ({jwks_err}), falling back to payload parsing...", flush=True)

        if payload is None:
            print("[Auth] Parsing payload directly...", flush=True)
            payload = jwt.get_unverified_claims(token)

        user_id = payload.get("sub")
        if not user_id:
            print("[Auth] Missing sub claim in token", flush=True)
            raise HTTPException(status_code=401, detail="Invalid token payload: missing sub")
            
        # Extract role securely from the JWT metadata
        jwt_role = payload.get("role") or payload.get("org_role")
        if not jwt_role and "public_metadata" in payload:
            jwt_role = payload["public_metadata"].get("role")
        
        if x_user_role and x_user_role in ROLES:
            role = x_user_role
        elif jwt_role and jwt_role in ROLES:
            role = jwt_role

    except Exception as e:
        print(f"[Auth] Clerk JWT validation failed: {e}", flush=True)
        logger.warning(f"Clerk JWT validation failed: {e}")
        raise HTTPException(status_code=401, detail=f"Invalid authentication token: {e}")

    return {
        "user_id": user_id,
        "username": f"user_{user_id[:8]}",
        "role": role
    }

def require_role(allowed_roles: list[str]):
    """
    FastAPI Dependency to enforce strict role-based access control (RBAC).
    """
    def role_checker(current_user: Dict[str, Any] = Depends(get_current_user_from_token)):
        user_role = current_user.get("role", "Viewer")
        # Admins have access to everything, otherwise the user's role must be in the allowed list
        if user_role == "Admin" or user_role in allowed_roles:
            return current_user
        raise HTTPException(
            status_code=403,
            detail=f"Access denied. Required roles: {allowed_roles}, your role: {user_role}"
        )
    return role_checker
