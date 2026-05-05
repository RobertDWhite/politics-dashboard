import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import config
from app.routers import accounts, articles, config as config_router
from app.services.digest import digest_loop
from app.services.feeds import refresh_articles, refresh_loop
from app.services.summarizer import summarizer_worker
from app.services.twitter import summarizer_loop as twitter_loop

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await refresh_articles()
    asyncio.create_task(refresh_loop())
    asyncio.create_task(summarizer_worker())
    asyncio.create_task(twitter_loop())
    asyncio.create_task(digest_loop())
    yield


app = FastAPI(title=f"{config.title} API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(articles.router)
app.include_router(accounts.router)
app.include_router(config_router.router)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/refresh")
async def refresh():
    await refresh_articles()
    return {"status": "ok"}
