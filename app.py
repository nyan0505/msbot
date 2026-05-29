from __future__ import annotations

import ipaddress

from aiohttp import web
from microsoft_agents.hosting.aiohttp import CloudAdapter, jwt_authorization_middleware
from microsoft_agents.hosting.core import TurnContext
from microsoft_agents.hosting.core.authorization import AgentAuthConfiguration, AuthTypes, JwtTokenValidator

import config
from bot import TeamsBot

auth_config = AgentAuthConfiguration(
    auth_type=AuthTypes.client_secret,
    client_id=config.APP_ID,
    client_secret=config.APP_SECRET,
    tenant_id=config.TENANT_ID,
)

bot = TeamsBot()
adapter = CloudAdapter()


def _is_loopback_request(request: web.Request) -> bool:
    remote = request.remote
    if not remote:
        return False
    try:
        return ipaddress.ip_address(remote).is_loopback
    except ValueError:
        return remote in {"localhost"}


def _cors_headers(request: web.Request) -> dict[str, str]:
    origin = request.headers.get("Origin")
    if not origin:
        return {}
    requested_headers = request.headers.get("Access-Control-Request-Headers")
    allow_headers = requested_headers or "Authorization,Content-Type,Accept"
    return {
        "Access-Control-Allow-Origin": origin,
        "Vary": "Origin",
        "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
        "Access-Control-Allow-Headers": allow_headers,
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Max-Age": "600",
    }


@web.middleware
async def local_dev_auth_middleware(request: web.Request, handler):
    # Web Chat may perform browser preflight before POSTing activities.
    if request.method == "OPTIONS":
        return web.Response(status=204, headers=_cors_headers(request))

    if _is_loopback_request(request) and not request.headers.get("Authorization"):
        request["claims_identity"] = JwtTokenValidator(auth_config).get_anonymous_claims()
        return await handler(request)
    return await jwt_authorization_middleware(request, handler)


@web.middleware
async def request_debug_middleware(request: web.Request, handler):
    response = await handler(request)
    for key, value in _cors_headers(request).items():
        response.headers.setdefault(key, value)
    print(
        f"[{request.method}] {request.path} remote={request.remote} "
        f"auth={'yes' if request.headers.get('Authorization') else 'no'} "
        f"status={response.status}"
    )
    return response


async def _on_turn_error(context: TurnContext, error: Exception) -> None:
    print(f"[on_turn_error] {type(error).__name__}: {error}")
    await context.send_activity("처리 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")


adapter.on_turn_error = _on_turn_error


async def messages(req: web.Request) -> web.Response:
    return await adapter.process(req, bot)


app = web.Application(middlewares=[request_debug_middleware, local_dev_auth_middleware])
app["agent_configuration"] = auth_config
app.router.add_get("/api/messages", lambda _: web.Response(status=200))
app.router.add_options("/api/messages", lambda _: web.Response(status=204))
app.router.add_post("/api/messages", messages)

if __name__ == "__main__":
    print("Bot server starting on port 3978...")
    web.run_app(app, host=["0.0.0.0", "::"], port=3978)
