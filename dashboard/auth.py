import time
from typing import Dict, Any, Optional

import jwt
from flask import request, abort, g, Flask
from pydantic import BaseModel, Field, field_validator, ValidationError

from .config import Settings, get_settings


class JWTClaims(BaseModel):
    """Pydantic model for normalized JWT claims used by the app."""

    sub: str
    name: Optional[str] = None
    role: str = Field(default="Developer")
    team: Optional[str] = None
    exp: int

    @field_validator("role", mode="before")
    @classmethod
    def normalize_role(cls, v):
        role = (v or "Developer") if isinstance(v, str) else "Developer"
        role_map = {
            "CIO": "CIO",
            "ChiefInformationOfficer": "CIO",
            "Architect": "Architect",
            "EnterpriseArchitect": "Architect",
            "SystemArchitect": "Architect",
            "SolutionArchitect": "Architect",
            "Developer": "Developer",
            "Engineer": "Developer",
        }
        return role_map.get(role, "Developer")


class AuthService:
    """Class-based JWT auth service handling guard and claims access."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()

    def _decode_jwt(self, token: str) -> dict:
        """Decode and validate a JWT (HS256 by default)."""
        options = {"require": ["exp"], "verify_exp": True}
        kwargs: Dict[str, Any] = {"algorithms": ["HS256"]}
        if self.settings.jwt_issuer:
            kwargs["issuer"] = self.settings.jwt_issuer
        if self.settings.jwt_audience:
            kwargs["audience"] = self.settings.jwt_audience
        return jwt.decode(token, self.settings.jwt_secret, options=options, **kwargs)

    def default_claims(self) -> dict:
        # Safe local dev defaults
        model = JWTClaims(
            sub="devuser@example.com",
            name="Dev User",
            role="Developer",
            team="Platform",
            exp=int(time.time()) + 3600,
        )
        return model.model_dump()

    def current_claims(self) -> dict:
        """Access JWT claims for this request (fallback to defaults in dev)."""
        return getattr(g, "claims", self.default_claims())

    def init_app(self, server: Flask) -> None:
        """Register a before_request auth guard on the Flask server."""

        @server.before_request
        def require_auth():
            path = request.path or ""
            if path.startswith("/assets") or path == "/health":
                return None

            if self.settings.disable_auth:
                g.claims = self.default_claims()
                return None

            auth = request.headers.get("Authorization", "")
            if not auth.startswith("Bearer "):
                abort(401, description="Missing or invalid Authorization header")

            token = auth.split(" ", 1)[1].strip()
            try:
                decoded = self._decode_jwt(token)
                claims_obj = JWTClaims.model_validate(decoded)
                claims = claims_obj.model_dump()
            except (Exception, ValidationError) as e:  # noqa: BLE001
                abort(401, description=f"Invalid token: {e}")

            g.claims = claims
            return None


# Backward-compatible module-level singletons and functions
_auth_service = AuthService()


def current_claims():
    return _auth_service.current_claims()


def init_auth(server: Flask) -> None:
    _auth_service.init_app(server)
