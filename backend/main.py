from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from database import supabase
from datetime import datetime, timezone
from typing import Optional
from contextlib import asynccontextmanager
import asyncio
from scraper import fetch_and_store

async def scrape_loop():
    while True:
        print("[scheduler] Running hourly scrape...")
        try:
            fetch_and_store()
        except Exception as e:
            print(f"[scheduler] Error: {e}")
        await asyncio.sleep(3600)

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[startup] Initial scrape...")
    try:
        fetch_and_store()
    except Exception as e:
        print(f"[startup] Error: {e}")
    task = asyncio.create_task(scrape_loop())
    yield
    task.cancel()

app = FastAPI(title="Khobor.ai API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ALL_SOURCES    = ["Prothom Alo", "BBC Bangla", "Kaler Kantho", "bdnews24"]
ALL_CATEGORIES = ["জাতীয়", "আন্তর্জাতিক", "খেলাধুলা", "ব্যবসা", "বিনোদন", "প্রযুক্তি"]

@app.get("/")
def root():
    return {"message": "Khobor.ai API is running"}

@app.get("/api/sources")
def get_sources():
    return {"sources": ALL_SOURCES}

@app.get("/api/categories")
def get_categories():
    return {"categories": ALL_CATEGORIES}

@app.delete("/api/dev/clear")
def clear_table():
    supabase.table("news_articles") \
        .delete() \
        .neq("id", "00000000-0000-0000-0000-000000000000") \
        .execute()
    return {"message": "Table cleared"}

@app.post("/api/dev/refresh")
def force_refresh():
    supabase.table("news_articles") \
        .delete() \
        .neq("id", "00000000-0000-0000-0000-000000000000") \
        .execute()
    count = fetch_and_store()
    return {"message": f"Refreshed. Inserted {count} articles."}

@app.get("/api/news/today")
def get_today_news(
    sources:    Optional[str] = Query(None),
    categories: Optional[str] = Query(None),
):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    preferred_sources = [s.strip() for s in sources.split(",")] if sources else ALL_SOURCES
    preferred_cats    = [c.strip() for c in categories.split(",")] if categories else ALL_CATEGORIES

    articles = []

    for source in preferred_sources:
        result = supabase.table("news_articles") \
            .select("id, title, summary, ai_summary, source, category, content_url, published_at") \
            .gte("fetched_at", f"{today}T00:00:00+00:00") \
            .eq("source", source) \
            .order("fetched_at", desc=True) \
            .limit(20) \
            .execute()

        source_articles = result.data

        matched   = [a for a in source_articles if a.get("category") in preferred_cats]
        unmatched = [a for a in source_articles if a.get("category") not in preferred_cats]

        # Always show at least 3-4 per source even if category doesn't match perfectly
        to_add = matched[:4] if matched else source_articles[:4]
        if len(matched) < 3:
            to_add += unmatched[:2]

        articles.extend(to_add)

    if not articles:
        raise HTTPException(status_code=404, detail="No news found")

    return {"date": today, "articles": articles}