"""Claude API による要約エンジン（本番実装）。

`summarize.Summarizer` インターフェースの実装で、Mock と差し替え可能。
Anthropic 公式SDK(`anthropic`)を使い、構造化出力で
要約 / センチメント(強気・弱気・中立) / 一言コメント を必ずJSONで受け取る。

⚠️ これは「情報整理」のための要約であり、投資助言・売買推奨・将来予測は行わない
   （システムプロンプトで明示）。

必要環境変数: ANTHROPIC_API_KEY
"""
from __future__ import annotations

import json

from summarize import BEARISH, BULLISH, NEUTRAL, Insight, Summarizer

SYSTEM = (
    "あなたは株式ニュースを整理するアシスタントです。与えられた記事について日本語で:\n"
    "(1) 1〜2文で要約する。\n"
    "(2) 対象銘柄にとっての市場センチメントを「強気」「弱気」「中立」のいずれかで判定する。\n"
    "(3) 対象銘柄への影響を一言コメントする。\n"
    "これは情報整理を目的とした要約であり、投資助言・売買推奨・将来予測ではありません。"
    "断定的な予測や売買の推奨は書かないでください。"
)

# 構造化出力スキーマ（必ずこの形のJSONで返る）
_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "sentiment": {"type": "string", "enum": [BULLISH, BEARISH, NEUTRAL]},
        "comment": {"type": "string"},
    },
    "required": ["summary", "sentiment", "comment"],
    "additionalProperties": False,
}

DEFAULT_MODEL = "claude-opus-4-8"  # 既定は最高性能。コスト重視は claude-haiku-4-5 へ。


class ClaudeSummarizer(Summarizer):
    name = "claude"

    def __init__(self, model: str | None = None):
        import anthropic  # 遅延import: mock利用時は anthropic 未インストールでも動く
        self._anthropic = anthropic
        self.client = anthropic.Anthropic()  # ANTHROPIC_API_KEY を環境から解決
        self.model = model or DEFAULT_MODEL

    def summarize(self, title: str, text: str, watched: list[str]) -> Insight:
        who = "・".join(watched) if watched else "市場全体"
        user = f"対象銘柄: {who}\n見出し: {title}\n本文: {text}"
        try:
            resp = self.client.messages.create(
                model=self.model,
                max_tokens=512,
                system=SYSTEM,
                messages=[{"role": "user", "content": user}],
                output_config={"format": {"type": "json_schema", "schema": _SCHEMA}},
            )
            text_out = next(b.text for b in resp.content if b.type == "text")
            data = json.loads(text_out)
            return Insight(summary=data["summary"],
                           sentiment=data["sentiment"],
                           comment=data["comment"])
        except self._anthropic.APIError as e:
            # API失敗時はパイプラインを止めず安全側にフォールバック
            return Insight(summary=(text or title)[:120], sentiment=NEUTRAL,
                           comment=f"(Claude要約に失敗: {type(e).__name__})")
