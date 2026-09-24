import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import config
from .db import init_db
from .routers import auth_routes, categories, rooms, panorama

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="360 Room Panorama App")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc):
    # Never leak raw stack traces / internals to the client
    from fastapi.responses import JSONResponse

    logging.getLogger("panorama.app").exception("Unhandled error on %s", request.url.path)
    return JSONResponse(status_code=500, content={"detail": "An unexpected error occurred."})


app.include_router(auth_routes.router)
app.include_router(categories.router)
app.include_router(rooms.router)
app.include_router(panorama.router)

# Serve the frontend (plain HTML/CSS/JS, no build step required)
app.mount("/", StaticFiles(directory=str(config.BASE_DIR / "frontend"), html=True), name="frontend")
