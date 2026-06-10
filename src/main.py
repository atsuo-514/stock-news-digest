"""CLI: 設定を読み、ニュースを収集→要約→ダイジェスト(Markdown/HTML)を出力する。

使い方:
  PYTHONPATH=src python -m main --sample                 # 同梱サンプルで即デモ（0円）
  PYTHONPATH=src python -m main --engine claude           # 本物のClaudeで要約（要APIキー）
  PYTHONPATH=src python -m main --full-text               # 記事本文もスクレイピング
"""
from __future__ import annotations

import argparse
import math
from datetime import date
from pathlib import Path

import yaml

import digest as D
import fetch
from summarize import get_summarizer

SAMPLE_FEED = "fixtures/sample_feed.xml"


def load_config(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="株ニュース AIダイジェスト")
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--sample", action="store_true",
                    help="同梱サンプルフィードを使う（オフラインデモ）")
    ap.add_argument("--engine", choices=["mock", "claude"], help="要約エンジン（config上書き）")
    ap.add_argument("--model", help="Claudeモデルid（config上書き）")
    ap.add_argument("--full-text", action="store_true", help="記事本文もスクレイピング")
    ap.add_argument("--out", default="output", help="出力ディレクトリ")
    args = ap.parse_args(argv)

    cfg = load_config(args.config)
    watchlist = cfg.get("watchlist", [])
    if args.sample:
        feeds = [SAMPLE_FEED]
    else:
        feeds = list(cfg.get("feeds") or [])
        if cfg.get("use_google_news"):
            feeds += fetch.google_news_feeds(
                watchlist,
                lang=cfg.get("google_news_lang", "ja"),
                country=cfg.get("google_news_country", "JP"),
            )
    if not feeds:
        print("フィードが未設定です。config.yaml の feeds / use_google_news を設定するか、--sample を使ってください。")
        return 1

    engine = args.engine or cfg.get("summarizer", "mock")
    model = args.model or cfg.get("claude_model")

    max_articles = cfg.get("max_articles", 20)
    per_feed = math.ceil(max_articles / len(feeds)) if len(feeds) > 1 else None
    print(f"[1/3] ニュース収集 … ソース {len(feeds)} 件")
    articles = fetch.collect(feeds, watchlist, max_articles=max_articles, per_feed=per_feed)
    print(f"      ウォッチ該当記事 {len(articles)} 件")
    if not articles:
        print("該当記事がありませんでした。")
        return 0

    if (args.full_text or cfg.get("fetch_full_text")) and not args.sample:
        print("      記事本文をスクレイピング中 …")
        sess = None
        for a in articles:
            a.full_text = fetch.fetch_full_text(a, interval=cfg.get("request_interval_sec", 1.0))

    print(f"[2/3] 要約 … エンジン={engine}")
    summarizer = get_summarizer(engine, model=model)
    items = D.build_items(articles, summarizer)

    day = date.today().isoformat()
    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / f"digest_{day}.md").write_text(
        D.to_markdown(items, day=day, engine=summarizer.name), encoding="utf-8")
    (outdir / f"digest_{day}.html").write_text(
        D.to_html(items, day=day, engine=summarizer.name), encoding="utf-8")
    print(f"[3/3] 出力 → {outdir}/digest_{day}.md / .html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
