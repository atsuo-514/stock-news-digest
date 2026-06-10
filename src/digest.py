"""ダイジェスト生成: 記事＋分析結果を Markdown / HTML に整形して出力する。"""
from __future__ import annotations

import html as html_lib
from collections import defaultdict
from datetime import date

from summarize import BEARISH, BULLISH, NEUTRAL

SENT_EMOJI = {BULLISH: "🟢", BEARISH: "🔴", NEUTRAL: "⚪"}
SENT_CLASS = {BULLISH: "pos", BEARISH: "neg", NEUTRAL: "neu"}
DISCLAIMER = ("本ダイジェストはニュースの情報整理を目的とした自動生成物です。"
              "投資助言ではなく、売買の推奨・将来予測を行うものではありません。")


def build_items(articles, summarizer):
    """各記事を要約エンジンにかけ、(Article, Insight) のリストを返す。"""
    return [(a, summarizer.summarize(a.title, a.text, a.matched)) for a in articles]


def aggregate(items) -> dict:
    """ウォッチ銘柄ごとに強気/弱気/中立の件数を集計。"""
    agg: dict[str, dict[str, int]] = defaultdict(lambda: {BULLISH: 0, BEARISH: 0, NEUTRAL: 0})
    for a, ins in items:
        for name in (a.matched or ["市場全体"]):
            agg[name][ins.sentiment] += 1
    return agg


def to_markdown(items, day: str | None = None, engine: str = "mock") -> str:
    day = day or date.today().isoformat()
    L = [f"# 📰 株ニュース AIダイジェスト — {day}", "",
         f"_対象記事 {len(items)} 件 ・ 要約エンジン: `{engine}`_", ""]

    agg = aggregate(items)
    if agg:
        L += ["## 🧭 銘柄別サマリー", "", "| 銘柄 | 🟢強気 | 🔴弱気 | ⚪中立 |", "|---|---|---|---|"]
        for name, c in agg.items():
            L.append(f"| {name} | {c[BULLISH]} | {c[BEARISH]} | {c[NEUTRAL]} |")
        L.append("")

    L += ["## 📝 記事ダイジェスト", ""]
    for a, ins in items:
        tag = SENT_EMOJI.get(ins.sentiment, "")
        L.append(f"### {tag} {a.title}")
        meta = []
        if a.matched:
            meta.append(" ".join(f"`{w}`" for w in a.matched))
        meta.append(ins.sentiment)
        L.append(" ・ ".join(meta))
        L += ["", ins.summary, "", f"> {ins.comment}", ""]
        if a.url:
            L.append(f"[記事を読む]({a.url})  ·  {a.published}")
        L += ["", "---", ""]

    L += ["", f"> ⚠️ {DISCLAIMER}"]
    return "\n".join(L)


def to_html(items, day: str | None = None, engine: str = "mock") -> str:
    day = day or date.today().isoformat()
    e = html_lib.escape

    rows = ""
    for name, c in aggregate(items).items():
        rows += (f"<tr><td>{e(name)}</td><td class='pos'>{c[BULLISH]}</td>"
                 f"<td class='neg'>{c[BEARISH]}</td><td class='neu'>{c[NEUTRAL]}</td></tr>")

    cards = ""
    for a, ins in items:
        cls = SENT_CLASS.get(ins.sentiment, "neu")
        tags = "".join(f"<span class='tag'>{e(w)}</span>" for w in a.matched)
        link = f"<a href='{e(a.url)}' target='_blank' rel='noopener'>記事を読む ↗</a>" if a.url else ""
        cards += f"""
      <article class="card {cls}">
        <div class="bar"></div>
        <div class="body">
          <div class="meta">{tags}<span class="sent {cls}">{e(ins.sentiment)}</span>
            <span class="date">{e(a.published)}</span></div>
          <h3>{e(a.title)}</h3>
          <p class="sum">{e(ins.summary)}</p>
          <p class="cmt">{e(ins.comment)}</p>
          <div class="link">{link}</div>
        </div>
      </article>"""

    return f"""<!doctype html><html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>株ニュース AIダイジェスト — {day}</title>
<style>
:root{{--bg:#0f1419;--panel:#161b22;--line:#2a3340;--text:#e8edf2;--sub:#8a94a0;
  --pos:#3fb950;--neg:#f85149;--neu:#8a94a0;--accent:#58a6ff;}}
*{{box-sizing:border-box;}}
body{{font-family:-apple-system,'Hiragino Sans','Yu Gothic',sans-serif;background:var(--bg);
  color:var(--text);margin:0;padding:28px;line-height:1.6;}}
.wrap{{max-width:860px;margin:0 auto;}}
h1{{font-size:24px;margin:0 0 4px;}} .lead{{color:var(--sub);font-size:13px;margin-bottom:22px;}}
table{{border-collapse:collapse;width:100%;background:var(--panel);border-radius:10px;overflow:hidden;
  margin-bottom:26px;}}
th,td{{padding:9px 12px;text-align:center;border-bottom:1px solid var(--line);font-size:14px;}}
th{{background:#1c232c;color:var(--sub);font-weight:600;}} td:first-child,th:first-child{{text-align:left;}}
.pos{{color:var(--pos);}} .neg{{color:var(--neg);}} .neu{{color:var(--neu);}}
.card{{display:flex;background:var(--panel);border:1px solid var(--line);border-radius:12px;
  overflow:hidden;margin-bottom:14px;}}
.card .bar{{width:5px;flex:none;}}
.card.pos .bar{{background:var(--pos);}} .card.neg .bar{{background:var(--neg);}} .card.neu .bar{{background:var(--neu);}}
.card .body{{padding:14px 18px;}}
.meta{{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:6px;}}
.tag{{background:#22303f;color:var(--accent);font-size:12px;padding:2px 8px;border-radius:99px;}}
.sent{{font-size:12px;font-weight:700;}} .sent.pos{{color:var(--pos);}} .sent.neg{{color:var(--neg);}} .sent.neu{{color:var(--neu);}}
.date{{color:var(--sub);font-size:12px;margin-left:auto;}}
.card h3{{font-size:17px;margin:2px 0 8px;}} .sum{{margin:0 0 8px;}}
.cmt{{margin:0;color:var(--sub);font-size:14px;border-left:3px solid var(--line);padding-left:10px;}}
.link{{margin-top:10px;}} .link a{{color:var(--accent);text-decoration:none;font-size:13px;}}
.disc{{margin-top:24px;color:var(--sub);font-size:12px;border-top:1px solid var(--line);padding-top:14px;}}
</style></head><body><div class="wrap">
<h1>📰 株ニュース AIダイジェスト</h1>
<div class="lead">{day} ・ 対象記事 {len(items)} 件 ・ 要約エンジン: {e(engine)}</div>
<table><thead><tr><th>銘柄</th><th>🟢強気</th><th>🔴弱気</th><th>⚪中立</th></tr></thead>
<tbody>{rows}</tbody></table>
{cards}
<div class="disc">⚠️ {e(DISCLAIMER)}</div>
</div></body></html>"""
