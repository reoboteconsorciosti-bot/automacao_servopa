import os
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
load_dotenv()


from app.routers.users import router as users_router
from app.routers.login import router as auth_router
from app.routers.automation import router as automation_router
from app.routers.pdfs import router as pdfs_router

app = FastAPI(
    title="Servopa Automação — Backend API",
    version="0.1.0",
    description="API REST de usuários e automação de lances de consórcio.",
)

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
DEBUG = os.getenv("DEBUG", "1") == "1"

origins = [
    FRONTEND_URL,
    "http://localhost:3000",
    "https://localhost:3000",
    "http://127.0.0.1:3000",
    "https://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
    "http://0.0.0.0:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1|0\.0\.0\.0)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)


@app.exception_handler(Exception)
async def catch_all_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    import traceback
    tb = traceback.format_exc()
    print(f"\n[ERRO 500] {request.method} {request.url.path}\n{tb}\n")
    if DEBUG:
        return JSONResponse(
            status_code=500,
            content={
                "detail": str(exc),
                "type": type(exc).__name__,
                "traceback": tb.splitlines()[-10:],
            },
        )
    return JSONResponse(
        status_code=500,
        content={"detail": "Erro interno no servidor. Contate o administrador."},
    )


app.include_router(users_router)
app.include_router(auth_router)
app.include_router(automation_router)
app.include_router(automation_router, prefix="/api")
app.include_router(pdfs_router)
app.include_router(pdfs_router, prefix="/api")


@app.get("/healthz", tags=["health"])
def health_check() -> dict:
    return {"status": "ok"}


@app.get("/debug/routes", tags=["debug"], include_in_schema=False)
def debug_routes() -> dict:
    from fastapi.routing import APIRoute

    def _walk(route_list, prefix: str = ""):
        routes = []
        for route in route_list:
            inner_prefix = prefix
            if hasattr(route, "include_context"):
                ctx = route.include_context
                inner_prefix = prefix + (ctx.prefix or "")
                routes.extend(_walk([ctx.included_router], inner_prefix))
            elif hasattr(route, "routes"):
                routes.extend(_walk(route.routes, inner_prefix + getattr(route, "prefix", "")))
            else:
                if isinstance(route, APIRoute):
                    routes.append({
                        "methods": sorted(route.methods or []),
                        "path": inner_prefix + route.path,
                        "name": route.name,
                    })
                elif hasattr(route, "path") and hasattr(route, "methods"):
                    routes.append({
                        "methods": sorted(route.methods or []),
                        "path": inner_prefix + route.path,
                    })
        return routes

    return {"routes": _walk(app.routes)}
