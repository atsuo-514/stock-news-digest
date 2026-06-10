"""ニュース収集レイヤー。

公開RSSフィードから記事を取得し、ウォッチリストのキーワードで絞り込む。
オプションで記事ページの本文を取得（個人利用・レート制御つきスクレイピング）。
RSSのソースはURLでもローカルファイルでも可（feedparser が両対応）＝オフラインデモ可能。
"""
from __future__ import annotations

import time
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


def collect(feeds: list[str], watchlist: list[dict], max_articles: int = 20) -> list[Article]:
    """フィード群から記事を集め、ウォッチに該当するものだけ返す（URLで重複排除）。"""
    seen: set[str] = set()
    out: list[Article] = []
    for src in feeds:
        feed = feedparser.parse(src)
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
            if len(out) >= max_articles:
                return out
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
