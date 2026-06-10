"""summarize.py（要約エンジン）のテスト。Mock のみ（claude はAPIキー要のため対象外）。"""
import pytest

import summarize as S
from summarize import BEARISH, BULLISH, NEUTRAL


def test_mock_sentiment():
    m = S.MockSummarizer()
    assert m._sentiment("上方修正で急騰") == BULLISH
    assert m._sentiment("続落して下落") == BEARISH
    assert m._sentiment("小動きで様子見") == NEUTRAL


def test_mock_extract_limits_sentences():
    m = S.MockSummarizer()
    assert m._extract("一文目。二文目。三文目。") == "一文目。二文目。"  # 先頭2文


def test_mock_summarize_shape():
    m = S.MockSummarizer()
    ins = m.summarize("トヨタ上方修正", "トヨタが上方修正。好調。", ["トヨタ自動車"])
    assert ins.sentiment == BULLISH
    assert "トヨタ自動車" in ins.comment
    assert ins.summary


def test_get_summarizer():
    assert isinstance(S.get_summarizer("mock"), S.MockSummarizer)
    with pytest.raises(ValueError):
        S.get_summarizer("unknown")
