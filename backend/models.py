from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class NewsArticle(BaseModel):
    id: Optional[str] = None
    title: str
    summary: Optional[str] = None
    content_url: str
    source: str
    published_at: Optional[datetime] = None
    fetched_at: Optional[datetime] = None
    is_processed: bool = False
    ai_summary: Optional[str] = None