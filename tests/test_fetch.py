"""fetch.py（ニュース収集）のテスト。同梱サンプルフィードで完全オフライン。"""
import os

import fetch

FIXTURE = os.path.join(os.path.dirname(__file__), "..", "fixtures", "sample_feed.xml")

WATCH = [
    {"name": "トヨタ自動車", "keywords": ["トヨタ", "Toyota"]},
    {"name": "半導体", "keywords": ["半導体", "NVIDIA"]},
    {"name": "日経平均", "keywords": ["日経平均"]},
]


def test_match_watchlist():
    assert fetch.match_watchlist("トヨタが上方修正", WATCH) == ["トヨタ自動車"]
    assert fetch.match_watchlist("NVIDIAの決算", WATCH) == ["半導体"]  # 大小無視で一致
    assert fetch.match_watchlist("無関係なニュース", WATCH) == []


def test_collect_filters_and_dedupes():
    arts = fetch.collect([FIXTURE], WATCH, max_articles=20)
    # サンプル6件のうち為替記事はウォッチ外 → 除外され5件
    assert len(arts) == 5
    assert all(a.matched for a in arts)                       # 全件ウォッチ該当
    assert not any("為替" in a.title for a in arts)           # ウォッチ外は含まれない


def test_collect_respects_max_articles():
    arts = fetch.collect([FIXTURE], WATCH, max_articles=2)
    assert len(arts) == 2


def test_article_text_priority():
    a = fetch.Article(title="T", url="u", summary_src="S")
    assert a.text == "S"          # 本文なし → RSS説明
    a.full_text = "F"
    assert a.text == "F"          # 本文あり → 本文優先


def test_google_news_feeds():
    feeds = fetch.google_news_feeds([{"name": "トヨタ自動車"}, {"name": ""}, {"keywords": ["x"]}])
    assert len(feeds) == 1        # name が空 / name 無し は除外
    assert feeds[0].startswith("https://news.google.com/rss/search?q=")
    assert "hl=ja" in feeds[0] and "gl=JP" in feeds[0]
