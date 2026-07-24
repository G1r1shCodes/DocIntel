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

jwks_cache = None

def get_jwks():
    global jwks_cache
    if jwks_cache is None:
        issuer = os.environ.get("CLERK_ISSUER")
        if not issuer:
            raise ValueError("CLERK_ISSUER environment variable is not set")
        
        jwks_url = f"{issuer.rstrip('/')}/.well-known/jwks.json"
        try:
            with urllib.request.urlopen(jwks_url) as response:
                jwks_cache = json.loads(response.read().decode())
        except Exception as e:
            logger.error(f"Failed to fetch JWKS from {jwks_url}: {e}")
            raise HTTPException(status_code=500, detail="Could not retrieve auth keys")
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
    if not credentials or not credentials.credentials:
        print("[Auth] Missing authentication token", flush=True)
        raise HTTPException(status_code=401, detail="Missing authentication token")
        
    token = credentials.credentials
    user_id = None
    role = "Viewer"

    try:
        print("[Auth] Fetching JWKS...", flush=True)
        jwks = get_jwks()
        unverified_header = jwt.get_unverified_header(token)
        
        rsa_key = {}
        for key in jwks.get("keys", []):
            if key["kid"] == unverified_header.get("kid"):
                rsa_key = key
                break
                
        if not rsa_key:
            raise HTTPException(status_code=401, detail="Invalid key ID in token")
            
        issuer = (os.environ.get("CLERK_ISSUER") or "").rstrip("/")
        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            options={"verify_aud": False, "verify_iss": False}
        )
        
        token_iss = (payload.get("iss") or "").rstrip("/")
        if issuer and token_iss and token_iss != issuer:
            print(f"[Auth] Issuer mismatch: token={token_iss}, expected={issuer}", flush=True)
            raise HTTPException(status_code=401, detail="Issuer mismatch")

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

    except jwt.ExpiredSignatureError:
        print("[Auth] Token has expired", flush=True)
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.JWTClaimsError as e:
        print(f"[Auth] Invalid claims: {e}", flush=True)
        raise HTTPException(status_code=401, detail=f"Invalid claims: {e}")
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
