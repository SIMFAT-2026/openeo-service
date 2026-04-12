from fastapi import FastAPI

from app.api.routes import config, health, jobs, openeo
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="SIMFAT openEO Service",
        version="0.1.0",
        description="Microservicio para obtencion de datos satelitales desde openEO.",
    )

    app.include_router(health.router)
    app.include_router(config.router)
    app.include_router(jobs.router)
    app.include_router(openeo.router)

    register_exception_handlers(app)

    @app.get("/", tags=["system"])
    def root() -> dict[str, str]:
        return {"service": "openeo-service", "env": settings.app_env}

    return app


app = create_app()
