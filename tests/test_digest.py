"""digest.py（ダイジェスト生成）のテスト。"""
import digest as D
import fetch
from summarize import BEARISH, BULLISH, MockSummarizer


def _items():
    arts = [
        fetch.Article(title="トヨタ上方修正で好調", url="u1",
                      summary_src="上方修正。", matched=["トヨタ自動車"]),
        fetch.Article(title="日経続落", url="u2",
                      summary_src="続落して下落。", matched=["日経平均"]),
    ]
    return D.build_items(arts, MockSummarizer())


def test_aggregate_counts():
    agg = D.aggregate(_items())
    assert agg["トヨタ自動車"][BULLISH] == 1
    assert agg["日経平均"][BEARISH] == 1


def test_markdown_contains_key_parts():
    md = D.to_markdown(_items(), day="2026-06-10", engine="mock")
    assert "株ニュース AIダイジェスト" in md
    assert "トヨタ上方修正で好調" in md
    assert "投資助言" in md          # ディスクレーマーが入る


def test_html_escapes_input():
    arts = [fetch.Article(title="<script>x</script>", url="u",
                          summary_src="t", matched=["A"])]
    html = D.to_html(D.build_items(arts, MockSummarizer()))
    assert "<script>x</script>" not in html   # 生のscriptは混入しない
    assert "&lt;script&gt;" in html           # エスケープされている
