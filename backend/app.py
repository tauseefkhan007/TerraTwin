"""Small OAuth backend for the NAKSH static dashboard.

Run locally with:
    uvicorn backend.app:app --host 127.0.0.1 --port 8001

Provider credentials are read only from environment variables. No provider
access tokens are stored in the session cookie or the repository.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urlparse

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DATA_DIR = PROJECT_ROOT / "dashboard"
POLICY_PATH = PROJECT_ROOT / "data" / "terratwin_source_policy.json"
FRONTEND_URL = os.getenv("TERRATWIN_FRONTEND_URL", "http://localhost:8000").rstrip("/")
SESSION_SECRET = os.getenv("TERRATWIN_SESSION_SECRET", "terratwin-local-development-secret")
SESSION_COOKIE = "terratwin_session"
SESSION_MAX_AGE = int(os.getenv("TERRATWIN_SESSION_MAX_AGE", "28800"))
COOKIE_SECURE = os.getenv("TERRATWIN_COOKIE_SECURE", "false").lower() == "true"

serializer = URLSafeTimedSerializer(SESSION_SECRET, salt="terratwin-session-v1")
oauth_states: dict[str, tuple[str, float]] = {}

PROVIDERS: dict[str, dict[str, Any]] = {
    "github": {
        "client_id": os.getenv("GITHUB_CLIENT_ID", ""),
        "client_secret": os.getenv("GITHUB_CLIENT_SECRET", ""),
        "redirect_uri": os.getenv("GITHUB_REDIRECT_URI", "http://localhost:8001/auth/github/callback"),
        "authorize_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "userinfo_url": "https://api.github.com/user",
        "scope": "read:user user:email",
    },
    "google": {
        "client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET", ""),
        "redirect_uri": os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8001/auth/google/callback"),
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": "https://openidconnect.googleapis.com/v1/userinfo",
        "scope": "openid email profile",
    },
}

app = FastAPI(title="NAKSH Auth API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


def provider_configured(provider: str) -> bool:
    config = PROVIDERS[provider]
    return bool(config["client_id"] and config["client_secret"])


def frontend_redirect(**params: str) -> RedirectResponse:
    query = urlencode(params)
    target = f"{FRONTEND_URL}/?{query}" if query else f"{FRONTEND_URL}/"
    return RedirectResponse(target, status_code=302)


def safe_next(value: str | None) -> str:
    if not value:
        return FRONTEND_URL + "/"
    parsed = urlparse(value)
    expected = urlparse(FRONTEND_URL)
    if parsed.scheme == expected.scheme and parsed.netloc == expected.netloc:
        return value
    return FRONTEND_URL + "/"


def remember_state(provider: str) -> str:
    state = secrets.token_urlsafe(32)
    oauth_states[state] = (provider, time.time() + 600)
    return state


def consume_state(state: str, provider: str) -> bool:
    stored = oauth_states.pop(state, None)
    if not stored:
        return False
    expected_provider, expires_at = stored
    return expected_provider == provider and time.time() < expires_at


def session_user(request: Request) -> dict[str, Any] | None:
    value = request.cookies.get(SESSION_COOKIE)
    if not value:
        return None
    try:
        return serializer.loads(value, max_age=SESSION_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None


def session_response(response: RedirectResponse, user: dict[str, Any]) -> RedirectResponse:
    response.set_cookie(
        SESSION_COOKIE,
        serializer.dumps(user),
        max_age=SESSION_MAX_AGE,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        path="/",
    )
    return response


def normalized_github_user(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "provider": "github",
        "id": str(payload.get("id", "")),
        "username": payload.get("login", ""),
        "name": payload.get("name") or payload.get("login", ""),
        "email": payload.get("email") or "",
        "avatar_url": payload.get("avatar_url") or "",
    }


def normalized_google_user(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "provider": "google",
        "id": str(payload.get("sub", "")),
        "username": payload.get("email", "").split("@", 1)[0],
        "name": payload.get("name") or payload.get("email", ""),
        "email": payload.get("email", ""),
        "avatar_url": payload.get("picture") or "",
    }


def _read_dashboard_json(filename: str) -> dict[str, Any]:
    path = FRONTEND_DATA_DIR / filename
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise HTTPException(status_code=503, detail=f"Dashboard data unavailable: {filename}") from error


def _read_policy() -> dict[str, Any]:
    try:
        return json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise HTTPException(status_code=503, detail="Source policy unavailable") from error


def _slug(value: str) -> str:
    return "-".join("".join(character.lower() if character.isalnum() else " " for character in value).split())


def _scientific_data() -> dict[str, Any]:
    return {
        "policy": _read_policy(),
        "source_lock": _read_dashboard_json("source_lock.json"),
        "data_audit": _read_dashboard_json("data_audit.json"),
        "dataset": _read_dashboard_json("analogx_dataset.json"),
        "terrain": _read_dashboard_json("terrain_rankings.json"),
        "target_catalog": _read_dashboard_json("target_sites.json"),
    }


def _earth_candidates(dataset: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = []
    for row in dataset.get("earth_features", []):
        candidates.append({
            "id": f"terrain-{_slug(row['name'])}",
            "body": "Earth",
            "record_type": "imported_earth_terrain",
            "name": row["name"],
            "country": row.get("country", ""),
            "lat": row.get("lat"),
            "lon": row.get("lon"),
            "elevation": row.get("elevation"),
            "terrain_features": {key: row.get(key) for key in ("slope", "roughness", "relief")},
            "data_source": row.get("data_source", ""),
            "evidence_status": "provisional_import",
        })
    return candidates


def _planetary_targets(target_catalog: dict[str, Any], body: str) -> list[dict[str, Any]]:
    return [{
        "id": site["id"],
        "body": site["body"],
        "record_type": "planetary_target_reference",
        "name": site["name"],
        "lat": site["lat"],
        "lon": site["lon"],
        "key_features": site.get("key_features", []),
        "evidence_status": "catalogue_reference",
        "source_note": site.get("source_note", ""),
    } for site in target_catalog.get("target_sites", []) if body == "all" or site.get("body", "").lower() == body]


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "service": "terratwin-auth",
        "providers": {name: provider_configured(name) for name in PROVIDERS},
    }


@app.get("/api/auth/config")
def auth_config() -> dict[str, Any]:
    return {"providers": {name: provider_configured(name) for name in PROVIDERS}}


@app.get("/api/datasets")
def datasets() -> dict[str, Any]:
    """Return the same provenance and integrity state used by the dashboard."""

    data = _scientific_data()
    source_lock = data["source_lock"]
    audit = data["data_audit"]
    dataset = data["dataset"]
    return {
        "project": "NAKSH",
        "challenge": "NASA Space Apps Challenge 2026",
        "official_resources_url": data["policy"]["official_resources_url"],
        "source_lock": {
            "ready": bool(source_lock.get("ready")),
            "status": source_lock.get("status"),
            "blocked_sources": len(source_lock.get("blocked_sources", [])),
            "missing_provenance": len(source_lock.get("missing_provenance", [])),
        },
        "data_audit": {
            "status": audit.get("status"),
            "errors": audit.get("errors", []),
            "counts": audit.get("counts", {}),
        },
        "imports": {
            "repository": dataset.get("source", {}).get("repository"),
            "commit": dataset.get("source", {}).get("commit"),
            "earth_feature_records": len(dataset.get("earth_features", [])),
            "planetary_target_records": len(dataset.get("planetary_targets", [])),
            "source_status": dataset.get("source", {}).get("source_lock_status"),
        },
    }


@app.get("/api/methodology")
def methodology() -> dict[str, Any]:
    data = _scientific_data()
    return {
        "official_resources_url": data["policy"]["official_resources_url"],
        "guardrails": data["policy"].get("required_guardrails", []),
        "source_lock": {
            "ready": bool(data["source_lock"].get("ready")),
            "status": data["source_lock"].get("status"),
        },
        "terrain_method": data["terrain"].get("method", {}),
        "provisional_note": "Imported repository terrain scores remain provisional until every displayed input passes the official Resources-tab provenance audit.",
    }


@app.get("/api/candidates")
def candidates(
    body: str = Query("all", pattern="^(all|earth|moon|mars)$"),
    target_id: str | None = None,
    limit: int = Query(50, ge=1, le=200),
) -> dict[str, Any]:
    data = _scientific_data()
    body = body.lower()
    items = []
    if body in {"all", "earth"}:
        items.extend(_earth_candidates(data["dataset"]))
    if body in {"all", "moon", "mars"}:
        items.extend(_planetary_targets(data["target_catalog"], body))
    if target_id:
        items = [item for item in items if item["id"] == target_id]
    return {
        "body": body,
        "target_id": target_id,
        "count": len(items),
        "limit": limit,
        "source_lock_ready": bool(data["source_lock"].get("ready")),
        "items": items[:limit],
    }


@app.get("/api/candidates/{candidate_id}/comparison")
def candidate_comparison(candidate_id: str, target_id: str | None = None) -> dict[str, Any]:
    data = _scientific_data()
    candidate = next((item for item in _earth_candidates(data["dataset"]) if item["id"] == candidate_id), None)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    target_rows = data["terrain"].get("targets", [])
    target = next((item for item in target_rows if not target_id or item.get("id") == target_id), None)
    if target is None:
        raise HTTPException(status_code=404, detail="Terrain target not found")
    ranking_rows = data["terrain"].get("rankings", {}).get(target["id"], [])
    ranking = next((row for row in ranking_rows if row.get("site_name") == candidate["name"]), None)
    source_ready = bool(data["source_lock"].get("ready"))
    return {
        "candidate": candidate,
        "target": {
            "id": target["id"],
            "body": target.get("world", "Mars"),
            "name": target.get("name"),
            "data_source": target.get("data_source"),
        },
        "comparison": {
            "similarity_score": ranking.get("score") if ranking and source_ready else None,
            "provisional_similarity_score": ranking.get("score") if ranking and not source_ready else None,
            "rank": ranking.get("rank") if ranking and source_ready else None,
            "coverage_score": 100 if ranking else 0,
            "status": "source_verified" if source_ready else "provisional_source_lock_pending",
            "guardrail": "Terrain similarity is not a landing-site safety assessment or environmental equivalence claim.",
        },
    }


@app.get("/api/candidates/{candidate_id}")
def candidate(candidate_id: str) -> dict[str, Any]:
    data = _scientific_data()
    all_items = _earth_candidates(data["dataset"]) + _planetary_targets(data["target_catalog"], "all")
    item = next((item for item in all_items if item["id"] == candidate_id), None)
    if item is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return {
        "item": item,
        "source_lock_ready": bool(data["source_lock"].get("ready")),
        "official_resources_url": data["policy"]["official_resources_url"],
    }


@app.get("/auth/{provider}")
def begin_auth(provider: str, next_url: str | None = None):
    if provider not in PROVIDERS:
        return frontend_redirect(auth="error", reason="unknown_provider")
    config = PROVIDERS[provider]
    if not provider_configured(provider):
        return frontend_redirect(auth="error", provider=provider, reason="provider_not_configured")
    state = remember_state(provider)
    params = {
        "client_id": config["client_id"],
        "redirect_uri": config["redirect_uri"],
        "response_type": "code",
        "scope": config["scope"],
        "state": state,
    }
    if provider == "google":
        params["access_type"] = "online"
        params["include_granted_scopes"] = "true"
    response = RedirectResponse(f'{config["authorize_url"]}?{urlencode(params)}', status_code=302)
    response.headers["X-TerraTwin-Next"] = safe_next(next_url)
    return response


@app.get("/auth/{provider}/callback")
def finish_auth(provider: str, request: Request, code: str | None = None, state: str | None = None):
    if provider not in PROVIDERS:
        return frontend_redirect(auth="error", reason="unknown_provider")
    if not code or not state or not consume_state(state, provider):
        return frontend_redirect(auth="error", provider=provider, reason="invalid_oauth_state")
    config = PROVIDERS[provider]
    try:
        token_response = requests.post(
            config["token_url"],
            data={
                "client_id": config["client_id"],
                "client_secret": config["client_secret"],
                "code": code,
                "redirect_uri": config["redirect_uri"],
                "grant_type": "authorization_code",
            },
            headers={"Accept": "application/json"},
            timeout=15,
        )
        token_response.raise_for_status()
        token = token_response.json().get("access_token")
        if not token:
            raise RuntimeError("OAuth provider returned no access token")
        user_response = requests.get(
            config["userinfo_url"],
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json", "User-Agent": "NAKSH/0.1"},
            timeout=15,
        )
        user_response.raise_for_status()
        payload = user_response.json()
        user = normalized_github_user(payload) if provider == "github" else normalized_google_user(payload)
        if not user["id"]:
            raise RuntimeError("OAuth provider returned no stable user identifier")
    except (requests.RequestException, ValueError, RuntimeError) as error:
        digest = hashlib.sha256(str(error).encode("utf-8")).hexdigest()[:10]
        return frontend_redirect(auth="error", provider=provider, reason=f"oauth_exchange_failed_{digest}")
    response = frontend_redirect(auth="success", provider=provider)
    return session_response(response, user)


@app.get("/api/me")
def current_user(request: Request) -> dict[str, Any]:
    user = session_user(request)
    return {"authenticated": bool(user), "user": user}


@app.post("/auth/logout")
def logout():
    response = JSONResponse({"ok": True})
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response
