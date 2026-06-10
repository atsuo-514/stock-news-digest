"""ニュース収集レイヤー。

公開RSSフィードから記事を取得し、ウォッチリストのキーワードで絞り込む。
オプションで記事ページの本文を取得（個人利用・レート制御つきスクレイピング）。
RSSのソースはURLでもローカルファイルでも可（feedparser が両対応）＝オフラインデモ可能。
"""
from __future__ import annotations

import time
import urllib.parse
from dataclasses import dataclass, field

import feedparser
import requests
from bs4 import BeautifulSoup

UA = "Mozilla/5.0 (compatible; stock-news-digest/0.1; personal use)"


@dataclass
class Article:
    title: str
    url: str
    published: str = ""
    summary_src: str = ""          # RSS の description（元の短い説明）
    full_text: str = ""            # 記事ページから取得した本文（任意）
    matched: list[str] = field(default_factory=list)  # マッチしたウォッチ銘柄名

    @property
    def text(self) -> str:
        """要約に渡す本文（本文 > RSS説明 > タイトル の優先順）。"""
        return self.full_text or self.summary_src or self.title


def _clean(html: str) -> str:
    return BeautifulSoup(html or "", "html.parser").get_text(" ", strip=True)


def match_watchlist(text: str, watchlist: list[dict]) -> list[str]:
    """text に含まれるウォッチ銘柄名を返す（name + keywords を大文字小文字無視で照合）。"""
    low = text.lower()
    hits = []
    for w in watchlist:
        terms = [w.get("name", "")] + list(w.get("keywords", []))
        if any(t and t.lower() in low for t in terms):
            hits.append(w["name"])
    return hits


def google_news_feeds(watchlist: list[dict], lang: str = "ja", country: str = "JP") -> list[str]:
    """ウォッチ銘柄名から Google News RSS 検索フィードのURLを生成する（実ニュース取得用）。

    Google News の検索RSSは公開エンドポイントで、銘柄名で実際の最新ニュースが取れる。
    """
    feeds = []
    for w in watchlist:
        q = (w.get("name") or "").strip()
        if not q:
            continue
        qs = urllib.parse.quote(q)
        feeds.append(
            f"https://news.google.com/rss/search?q={qs}&hl={lang}&gl={country}&ceid={country}:{lang}"
        )
    return feeds


def collect(feeds: list[str], watchlist: list[dict], max_articles: int = 20,
            per_feed: int | None = None) -> list[Article]:
    """フィード群から記事を集め、ウォッチに該当するものだけ返す（URLで重複排除）。

    per_feed を指定すると各フィードからの採用数を上限で揃える（銘柄が偏らないように）。
    """
    seen: set[str] = set()
    out: list[Article] = []
    for src in feeds:
        feed = feedparser.parse(src)
        n_src = 0
        for e in feed.entries:
            url = e.get("link", "")
            if url in seen:
                continue
            seen.add(url)
            title = e.get("title", "")
            desc = _clean(e.get("summary", ""))
            matched = match_watchlist(f"{title} {desc}", watchlist)
            if watchlist and not matched:
                continue  # ウォッチに無関係な記事は除外
            out.append(Article(title=title, url=url,
                               published=e.get("published", ""),
                               summary_src=desc, matched=matched))
            n_src += 1
            if len(out) >= max_articles:
                return out
            if per_feed and n_src >= per_feed:
                break  # このフィードからの採用は上限まで → 次の銘柄へ
    return out


def fetch_full_text(article: Article, session: requests.Session | None = None,
                    interval: float = 1.0, max_chars: int = 4000) -> str:
    """記事ページ本文を簡易スクレイピング（<p> テキストを連結）。失敗時は空文字。"""
    sess = session or requests.Session()
    try:
        time.sleep(interval)  # サイト負荷に配慮（1リクエスト1秒）
        r = sess.get(article.url, timeout=10, headers={"User-Agent": UA})
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        paras = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
        text = "\n".join(p for p in paras if len(p) > 20)
        return text[:max_chars]
    except Exception:
        return ""  # 取得失敗は本文なしで続行（RSS説明で要約する）
