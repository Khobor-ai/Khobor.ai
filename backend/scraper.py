import feedparser
from datetime import datetime, timezone
from database import supabase

FEEDS = {
    "Prothom Alo":  "https://www.prothomalo.com/feed/",
    "BBC Bangla":   "https://feeds.bbci.co.uk/bengali/rss.xml",
    "Kaler Kantho": "https://www.kalerkantho.com/rss.xml",
    "bdnews24":     "https://bdnews24.com/?widgetName=rssfeed&widgetId=1091&getXmlFeed=true",
}

LIMIT_PER_SOURCE = 30

CATEGORY_KEYWORDS = {
    "খেলাধুলা":    ["ক্রিকেট", "ফুটবল", "খেলা", "টুর্নামেন্ট", "বিশ্বকাপ", "ম্যাচ",
                    "cricket", "football", "sport", "ipl", "বিপিএল", "টেস্ট", "ওয়ানডে"],
    "ব্যবসা":      ["অর্থনীতি", "ব্যবসা", "বাজার", "শেয়ার", "ব্যাংক", "বিনিয়োগ",
                    "রপ্তানি", "আমদানি", "মূল্যস্ফীতি", "টাকা", "ডলার", "বাজেট", "রাজস্ব"],
    "বিনোদন":      ["সিনেমা", "চলচ্চিত্র", "নাটক", "গান", "অভিনেতা", "অভিনেত্রী",
                    "তারকা", "সেলিব্রিটি", "বিনোদন", "ওটিটি", "শিল্পী", "সংগীত", "নায়ক", "নায়িকা"],
    "প্রযুক্তি":   ["প্রযুক্তি", "মোবাইল", "ইন্টারনেট", "কৃত্রিম", "এআই", "সফটওয়্যার",
                    "অ্যাপ", "স্মার্টফোন", "সাইবার", "ডিজিটাল", "রোবট", "স্যাটেলাইট"],
    "আন্তর্জাতিক": ["আন্তর্জাতিক", "বিশ্ব", "যুক্তরাষ্ট্র", "ভারত", "চীন", "রাশিয়া",
                    "ইউক্রেন", "ইসরায়েল", "ফিলিস্তিন", "জাতিসংঘ", "ইরান", "পাকিস্তান",
                    "যুদ্ধ", "মার্কিন", "ট্রাম্প", "ন্যাটো", "ইউরোপ"],
    "জাতীয়":      [],
}

def classify_category(title: str, summary: str) -> str:
    text = (title + " " + summary).lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if category == "জাতীয়":
            continue
        if any(kw.lower() in text for kw in keywords):
            return category
    return "জাতীয়"

def title_words(title):
    return set(title.lower().split())

def is_duplicate(new_title, seen_titles, threshold=0.6):
    new_words = title_words(new_title)
    for seen in seen_titles:
        seen_words = title_words(seen)
        if not new_words or not seen_words:
            continue
        overlap = len(new_words & seen_words) / max(len(new_words), len(seen_words))
        if overlap >= threshold:
            return True
    return False

def fetch_and_store():
    inserted = 0
    skipped_url = 0
    skipped_sim = 0

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    existing = supabase.table("news_articles") \
        .select("title") \
        .gte("fetched_at", f"{today}T00:00:00+00:00") \
        .execute()
    seen_titles = [r["title"] for r in existing.data]

    for source, url in FEEDS.items():
        feed = feedparser.parse(url)
        print(f"[{source}] {len(feed.entries)} entries found")
        count = 0

        for entry in feed.entries:
            if count >= LIMIT_PER_SOURCE:
                break

            title       = entry.get("title", "").strip()
            content_url = entry.get("link", "").strip()
            summary     = entry.get("summary", "").strip()

            if not title or not content_url:
                continue

            existing_url = supabase.table("news_articles") \
                .select("id").eq("content_url", content_url).execute()
            if existing_url.data:
                skipped_url += 1
                count += 1
                continue

            if is_duplicate(title, seen_titles):
                skipped_sim += 1
                count += 1
                continue

            category = classify_category(title, summary)

            published_at = None
            if entry.get("published_parsed"):
                published_at = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).isoformat()

            row = {
                "title":        title,
                "summary":      summary,
                "content_url":  content_url,
                "source":       source,
                "category":     category,
                "published_at": published_at,
                "fetched_at":   datetime.now(timezone.utc).isoformat(),
                "is_processed": False,
                "ai_summary":   None,
            }

            supabase.table("news_articles").insert(row).execute()
            seen_titles.append(title)
            inserted += 1
            count += 1
            print(f"  ✓ [{category}] {title[:60]}")

    print(f"\nDone. Inserted: {inserted} | URL dupes: {skipped_url} | Similar skipped: {skipped_sim}")
    return inserted

if __name__ == "__main__":
    fetch_and_store()