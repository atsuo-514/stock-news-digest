"""要約レイヤー（差し替え式）。

Summarizer インターフェースを実装で差し替える:
  - MockSummarizer   : APIなし・ルールベース（0円で動く。CI/デモ用）
  - ClaudeSummarizer : Anthropic Claude API（ANTHROPIC_API_KEY が必要）

呼び出し側は get_summarizer(name) を使うだけで、要約エンジンを意識しない。
"""
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass

# 強気/弱気を判定するための簡易キーワード（モック用）
POSITIVE = ["上方修正", "急騰", "好決算", "上回る", "好調", "改善", "前倒し", "最高益",
            "増益", "上昇", "回復", "拡大", "堅調", "上振れ", "買い"]
NEGATIVE = ["下方修正", "急落", "続落", "下落", "減益", "赤字", "停止", "遅れ",
            "低迷", "悪化", "縮小", "下振れ", "懸念", "リスク", "売り"]

BULLISH, BEARISH, NEUTRAL = "強気", "弱気", "中立"


@dataclass
class Insight:
    """1記事に対する分析結果。"""
    summary: str          # 1〜2文の要約
    sentiment: str        # 強気 / 弱気 / 中立
    comment: str          # ウォッチ銘柄への一言


class Summarizer(ABC):
    name = "base"

    @abstractmethod
    def summarize(self, title: str, text: str, watched: list[str]) -> Insight:
        ...


class MockSummarizer(Summarizer):
    """APIを使わない簡易要約。先頭文の抽出＋キーワードによる強弱判定。

    本物のClaudeに差し替える前提の「動く土台」。0円・オフラインで全工程を通せる。
    """
    name = "mock"

    def summarize(self, title: str, text: str, watched: list[str]) -> Insight:
        return Insight(
            summary=self._extract(text or title),
            sentiment=self._sentiment(f"{title} {text}"),
            comment=self._comment(watched, self._sentiment(f"{title} {text}")),
        )

    @staticmethod
    def _extract(text: str, max_sentences: int = 2, max_chars: int = 120) -> str:
        sentences = [s.strip() for s in re.split(r"(?<=。)", text) if s.strip()]
        out = "".join(sentences[:max_sentences]) or text
        return out[:max_chars]

    @staticmethod
    def _sentiment(text: str) -> str:
        pos = sum(text.count(w) for w in POSITIVE)
        neg = sum(text.count(w) for w in NEGATIVE)
        if pos > neg:
            return BULLISH
        if neg > pos:
            return BEARISH
        return NEUTRAL

    @staticmethod
    def _comment(watched: list[str], sentiment: str) -> str:
        who = "・".join(watched) if watched else "市場全体"
        label = {BULLISH: "ポジティブ材料", BEARISH: "ネガティブ材料",
                 NEUTRAL: "中立的な内容"}[sentiment]
        return f"{who}に関する{label}。"


def get_summarizer(name: str = "mock", model: str | None = None) -> Summarizer:
    """要約エンジンを名前で取得。'claude' は遅延importでanthropic未導入でも他は動く。"""
    if name == "mock":
        return MockSummarizer()
    if name == "claude":
        from claude_summarizer import ClaudeSummarizer  # 遅延import
        return ClaudeSummarizer(model=model)
    raise ValueError(f"unknown summarizer: {name}")
