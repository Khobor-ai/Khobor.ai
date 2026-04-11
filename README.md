# Khobor.ai 📰
Ai news aggregator for Bengali language.

## Phase 1 — News Ingestion + Display
- Scrapes: Prothom Alo, BBC Bangla, bdnews24
- Backend: FastAPI + Supabase
- Frontend: HTML + Tailwind CSS

## Setup
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env  # Fill in Supabase credentials
uvicorn main:app --reload
```

## Supabase Table SQL
```sql
create table news_articles (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  summary text,
  content_url text unique not null,
  source text,
  published_at timestamptz,
  fetched_at timestamptz,
  is_processed boolean default false,
  ai_summary text
);
```