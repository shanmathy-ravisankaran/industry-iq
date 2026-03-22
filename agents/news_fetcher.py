import os
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
from dotenv import load_dotenv

try:
    from newsapi import NewsApiClient
except Exception:
    NewsApiClient = None


load_dotenv()


INDUSTRY_KEYWORDS = {
    "hotels": "hotel hospitality resort",
    "airlines": "airline aviation flight",
    "finance": "finance stock market",
}

NEWS_CST = ZoneInfo("America/Chicago")


def load_financial_news_sample(n: int = 50) -> list[str]:
    csv_path = os.path.join("data", "sentiment", "all-data.csv")
    df = pd.read_csv(
        csv_path,
        encoding="latin-1",
        header=None,
        names=["label", "text"],
    )
    return df["text"].dropna().head(n).tolist()


def build_query(brand: str, industry: str) -> str:
    keyword_string = INDUSTRY_KEYWORDS.get(industry.lower(), industry.lower())
    return f'"{brand}" ({keyword_string})'


def published_at_to_cst(published_at: str | None) -> str | None:
    # NewsAPI returns publishedAt in UTC; normalize to America/Chicago before storing or displaying.
    if not published_at:
        return None
    try:
        utc_dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        return utc_dt.astimezone(NEWS_CST).strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def fetch_live_headlines(brand: str, industry: str, page_size: int = 50) -> list[str]:
    api_key = os.getenv("NEWSAPI_KEY")
    if not api_key or NewsApiClient is None:
        return []

    try:
        client = NewsApiClient(api_key=api_key)
        response = client.get_everything(
            q=build_query(brand, industry),
            language="en",
            sort_by="publishedAt",
            page_size=page_size,
        )
        articles = response.get("articles", [])
        headlines: list[str] = []
        seen: set[str] = set()

        for article in articles:
            title = (article.get("title") or "").strip()
            description = (article.get("description") or "").strip()
            _published_cst = published_at_to_cst(article.get("publishedAt"))
            text = " - ".join(part for part in [title, description] if part)
            if not text:
                continue

            normalized = text.lower()
            if normalized in seen:
                continue

            seen.add(normalized)
            headlines.append(text)

            if len(headlines) >= page_size:
                break

        return headlines
    except Exception as e:
        print(f"[NewsFetcher] NewsAPI failed: {e}")
        return []


def fetch_headlines(brand: str, industry: str, page_size: int = 50) -> list[str]:
    headlines = fetch_live_headlines(brand=brand, industry=industry, page_size=page_size)
    if len(headlines) >= 5:
        return headlines
    return load_financial_news_sample(page_size)
