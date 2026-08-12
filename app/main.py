from __future__ import annotations

import asyncio
import logging

from aiohttp import web
from redis.asyncio import Redis
from sqlalchemy import text

from app.common.logging import configure_logging
from app.config import get_settings
from app.db.session import make_engine, make_session_factory
from app.discord.bot import StudymeBot
from app.llm.router import build_provider

log = logging.getLogger(__name__)


async def create_health_app(engine, redis: Redis | None) -> web.Application:
    async def root(_: web.Request) -> web.Response:
        return web.json_response(
            {
                "service": "studyme-memory-bot",
                "version": "0.1.0",
                "status": "starting-or-ready",
            }
        )

    async def health(_: web.Request) -> web.Response:
        checks: dict[str, str] = {}
        try:
            async with engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
            checks["database"] = "ok"
        except Exception:
            checks["database"] = "error"
        if redis is not None:
            try:
                await redis.ping()
                checks["redis"] = "ok"
            except Exception:
                checks["redis"] = "error"
        ok = all(value == "ok" for value in checks.values())
        return web.json_response(
            {"status": "ok" if ok else "degraded", "checks": checks},
            status=200 if ok else 503,
        )

    app = web.Application()
    app.router.add_get("/", root)
    app.router.add_get("/health", health)
    return app


async def async_main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    engine = make_engine(settings.database_url)
    sessions = make_session_factory(engine)
    redis = (
        Redis.from_url(settings.redis_url, decode_responses=True) if settings.redis_url else None
    )

    runner = web.AppRunner(await create_health_app(engine, redis))
    await runner.setup()
    site = web.TCPSite(runner, settings.health_host, settings.port)
    await site.start()
    log.info("health server listening on %s:%d", settings.health_host, settings.port)

    bot: StudymeBot | None = None
    try:
        if settings.run_bot:
            token = settings.discord_token.get_secret_value()
            if not token:
                raise RuntimeError("RUN_BOT=true but DISCORD_TOKEN is empty")
            bot = StudymeBot(
                settings=settings,
                sessions=sessions,
                provider=build_provider(settings),
            )
            await bot.start(token)
        else:
            log.warning("RUN_BOT=false; health-only mode is active")
            await asyncio.Event().wait()
    finally:
        if bot and not bot.is_closed():
            await bot.close()
        if redis is not None:
            await redis.aclose()
        await engine.dispose()
        await runner.cleanup()


def run() -> None:
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    run()
