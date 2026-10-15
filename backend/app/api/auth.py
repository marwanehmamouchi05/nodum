"""Same-origin browser login and authenticated session dependencies."""
from datetime import datetime
from pathlib import Path
from html import escape
from typing import Annotated
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from app.api.dependencies import get_repository, utc_now
from app.auth_config import AuthSettings
from app.config import ConfigurationError
from app.services.auth import AuthService, csrf_token
from app.services.errors import DomainError

router = APIRouter(prefix="/auth", tags=["Authentication"])
WEB = Path(__file__).resolve().parents[1] / "web"
PRIVATE_HEADERS = {"Cache-Control": "no-store", "Referrer-Policy": "no-referrer",
                   "X-Content-Type-Options": "nosniff"}


def get_auth_settings():
    try:
        return AuthSettings.from_env()
    except ConfigurationError:
        raise DomainError(503, "Nodum authentication origin configuration is missing or invalid") from None


def get_auth_service(repository=Depends(get_repository), settings=Depends(get_auth_settings)):
    return AuthService(repository, settings)


Service = Annotated[AuthService, Depends(get_auth_service)]
Now = Annotated[datetime, Depends(utc_now)]


def cookie_value(request, service):
    return request.cookies.get(service.settings.cookie_name)


def get_current_user(request: Request, service: Service, now: Now):
    user = service.user(cookie_value(request, service), now)
    if not user:
        raise DomainError(401, "Sign in to Nodum to continue")
    return user


def require_csrf(request: Request, service: Service, now: Now):
    service.check_csrf(cookie_value(request, service), request.headers.get("x-csrf-token"),
                       request.headers.get("origin"), now)


def set_cookie(response, service, cookie, age):
    response.set_cookie(service.settings.cookie_name, cookie, max_age=age,
                        httponly=True, secure=service.settings.secure, samesite="lax", path="/")


def browser_page(continuation=""):
    markup = (WEB / "auth.html").read_text(encoding="utf-8").replace(
        'name="nodum-return" content=""', f'name="nodum-return" content="{escape(continuation, quote=True)}"')
    return HTMLResponse(markup, headers={
        **PRIVATE_HEADERS,
        "Content-Security-Policy": "default-src 'none'; script-src 'self'; style-src 'unsafe-inline'; connect-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'",
    })


@router.get("/login", response_class=HTMLResponse)
def login_page(return_to: str = "", settings: AuthSettings = Depends(get_auth_settings)):
    # Exact configured origin roots only. No arbitrary paths, protocol-relative
    # redirects, Host-derived authority, credentials, query strings or fragments.
    allowed = {origin + "/" for origin in (settings.public_origin, *settings.trusted_origins)}
    return browser_page(return_to if return_to in allowed else "")


@router.get("/client.js", include_in_schema=False)
def browser_script():
    return Response((WEB / "auth.js").read_text(encoding="utf-8"),
                    media_type="text/javascript", headers=PRIVATE_HEADERS)


@router.get("/session")
def session_context(request: Request, response: Response, service: Service, now: Now):
    cookie = cookie_value(request, service)
    if not service.session(cookie, now):
        cookie, age = service.issue(now, old_cookie=cookie,
                                    client_ip=request.client.host if request.client else "unknown")
        set_cookie(response, service, cookie, age)
    user = service.user(cookie, now)
    response.headers.update(PRIVATE_HEADERS)
    from app.services.authorization import authorization_mode, AuthorizationService
    from app.models.authorization import Principal
    from app.api.authorization import principal_context
    mode = authorization_mode()
    authorization = principal_context(AuthorizationService(service.repository,
        Principal(user_id=user.id, person_id=user.person_id), now)) if user and mode == "scoped" else None
    return {"user": user.public() if user else None, "csrf_token": csrf_token(cookie),
            "authorization_mode": mode, "authorization": authorization}


class LoginInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=1, max_length=128)
    password: SecretStr = Field(min_length=1, max_length=128)


@router.post("/login", dependencies=[Depends(require_csrf)])
def login(payload: LoginInput, request: Request, response: Response, service: Service, now: Now):
    user, cookie, age = service.login(payload.username, payload.password.get_secret_value(),
                                      cookie_value(request, service), now,
                                      request.client.host if request.client else "unknown")
    set_cookie(response, service, cookie, age)
    response.headers.update(PRIVATE_HEADERS)
    return {"user": user.public(), "csrf_token": csrf_token(cookie)}


@router.get("/me")
def current_user(response: Response, user=Depends(get_current_user)):
    response.headers.update(PRIVATE_HEADERS)
    return user.public()


@router.post("/logout", dependencies=[Depends(get_current_user), Depends(require_csrf)])
def logout(request: Request, response: Response, service: Service):
    service.logout(cookie_value(request, service))
    response.delete_cookie(service.settings.cookie_name, path="/", secure=service.settings.secure,
                           httponly=True, samesite="lax")
    response.headers.update(PRIVATE_HEADERS)
    return {"status": "signed_out"}
