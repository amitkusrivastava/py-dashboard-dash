import time

import jwt
import pytest

from dashboard.auth import AuthService, JWTClaims
from dashboard.config import Settings


def make_settings(**overrides):
    return Settings(**overrides)


def test_default_claims_used_when_disabled(monkeypatch):
    svc = AuthService(settings=make_settings(disable_auth=True, jwt_secret="s"))
    claims = svc.current_claims()
    assert claims["role"] == "Developer"
    assert "exp" in claims


def test_decode_and_role_mapping_valid_token():
    s = make_settings(jwt_secret="secret", disable_auth=False)
    svc = AuthService(settings=s)
    payload = {"sub": "cio@corp", "name": "CIO", "role": "ChiefInformationOfficer", "exp": int(time.time()) + 60}
    tok = jwt.encode(payload, s.jwt_secret, algorithm="HS256")
    decoded = svc._decode_jwt(tok)
    model = JWTClaims.model_validate(decoded)
    assert model.role == "CIO"


def test_decode_invalid_token_raises():
    s = make_settings(jwt_secret="secret")
    svc = AuthService(settings=s)
    with pytest.raises(Exception):
        svc._decode_jwt("not-a-token")
