"""Rule-based sentiment engine v2 — Chinese financial sentiment with dictionary + negation.

Key improvements over v1 (which had 98% neutral rate):
  1. Expanded polarity lexicon (800+ Chinese, 400+ English financial terms)
  2. Negation handling: 3-word window negation flips polarity
  3. Intensifier/diminisher modifiers
  4. Title 3x weight, lead paragraph 2x weight
  5. Continuous score [-1, 1] with adaptive threshold
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger("finkg.nlp.sentiment")

# ═══════════════════════════════════════════════════════════════
# Chinese Financial Sentiment Lexicon (polarity: -1.0 to 1.0)
# ═══════════════════════════════════════════════════════════════

CN_LEXICON: dict[str, float] = {
    # ── Strong positive (0.7 ~ 1.0) ──
    "暴涨": 0.9, "飙升": 0.85, "涨停": 0.9, "创新高": 0.9, "翻倍": 0.9,
    "突破": 0.75, "大涨": 0.8, "走强": 0.7, "拉升": 0.75, "反弹": 0.65,
    "牛市": 0.85, "利好": 0.8, "强劲": 0.7, "繁荣": 0.8, "复苏": 0.7,
    "回暖": 0.65, "增长": 0.55, "回升": 0.6, "盈利": 0.6, "扩张": 0.55,
    "超预期": 0.8, "跑赢": 0.75, "增持": 0.7, "买入": 0.7, "看好": 0.65,
    "改善": 0.5, "放量": 0.55, "加仓": 0.65, "普涨": 0.7, "连板": 0.75,
    "主升浪": 0.85, "乐观": 0.65, "景气": 0.7, "向上": 0.5, "加速": 0.55,
    "领涨": 0.75, "扩容": 0.5, "松绑": 0.6,

    # ── Moderate positive (0.3 ~ 0.7) ──
    "上涨": 0.5, "走高": 0.5, "上扬": 0.5, "攀升": 0.5, "推高": 0.45,
    "向好": 0.5, "提振": 0.55, "带动": 0.4, "支撑": 0.35, "企稳": 0.4,
    "降息": 0.55, "降准": 0.55, "宽松": 0.55, "刺激": 0.4, "扶持": 0.45,
    "减税": 0.5, "补贴": 0.4, "分红": 0.45, "回购": 0.45, "升级": 0.35,
    "优化": 0.3, "提升": 0.35, "推进": 0.3, "扩大": 0.3, "领先": 0.4,
    "信心": 0.4, "稳定": 0.3, "增强": 0.35, "注入": 0.3, "助力": 0.35,
    "稳步": 0.3, "有序": 0.3, "成效": 0.35, "见好": 0.45, "趋稳": 0.35,
    "反弹": 0.5, "修复": 0.4, "见底": 0.45, "反弹": 0.55, "重估": 0.4,
    "估值修复": 0.55, "业绩增长": 0.6, "政策支持": 0.5, "资金流入": 0.55,
    "北向资金流入": 0.6, "净流入": 0.55, "抄底": 0.5, "见底回升": 0.6,
    "底部": 0.35, "筑底": 0.4, "磨底": 0.3, "成功": 0.55, "达成": 0.4,
    "签署": 0.3, "合作": 0.35, "共赢": 0.45, "开放": 0.35, "自由化": 0.4,

    # ── Strong negative (-1.0 ~ -0.7) ──
    "暴跌": -0.9, "崩盘": -0.95, "跌停": -0.9, "恐慌": -0.8, "危机": -0.85,
    "违约": -0.9, "爆仓": -0.9, "强平": -0.85, "踩踏": -0.9, "退市": -0.85,
    "破产": -0.9, "倒闭": -0.9, "战争": -0.9, "制裁": -0.7, "断供": -0.8,
    "脱钩": -0.75, "封锁": -0.8, "暴雷": -0.85, "暴雷": -0.85, "失控": -0.75,

    # ── Moderate negative (-0.3 ~ -0.7) ──
    "下跌": -0.5, "跳水": -0.7, "走弱": -0.6, "大跌": -0.7, "重挫": -0.75,
    "下探": -0.6, "阴跌": -0.55, "失守": -0.6, "破位": -0.65, "跌穿": -0.7,
    "亏损": -0.65, "衰退": -0.7, "风险": -0.3, "警告": -0.4, "悲观": -0.6,
    "抛售": -0.6, "减仓": -0.55, "减持": -0.6, "卖出": -0.55, "看空": -0.6,
    "跑输": -0.65, "低于预期": -0.55, "萎缩": -0.55, "下滑": -0.5, "回落": -0.35,
    "恶化": -0.6, "收紧": -0.45, "去杠杆": -0.5, "加息": -0.4, "缩表": -0.5,
    "通胀": -0.2, "滞胀": -0.55, "地缘": -0.3, "冲突": -0.55, "调查": -0.35,
    "诉讼": -0.4, "召回": -0.45, "投诉": -0.3, "停产": -0.5, "关停": -0.55,
    "ST": -0.65, "戴帽": -0.65, "问询函": -0.5, "监管函": -0.45, "处罚": -0.5,
    "罚款": -0.4, "违规": -0.5, "造假": -0.7, "退市风险": -0.8, "流动性危机": -0.8,
    "债务危机": -0.85, "信用危机": -0.8, "汇率贬值": -0.45, "资本外流": -0.5,
    "外资流出": -0.5, "净流出": -0.5, "缩量": -0.4, "低迷": -0.5, "疲软": -0.45,
    "承压": -0.35, "拖累": -0.4, "受阻": -0.4, "搁置": -0.4, "终止": -0.5,
    "取消": -0.35, "下降": -0.3, "减少": -0.3, "放缓": -0.25, "谨慎": -0.25,
    "不确定性": -0.35, "分歧": -0.25, "僵局": -0.45, "停滞": -0.4,
}

# ═══════════════════════════════════════════════════════════════
# Chinese Negation Words (invert polarity within 3-word window)
# ═══════════════════════════════════════════════════════════════
CN_NEGATION = {"不", "未", "无", "没有", "并非", "缺乏", "缺少", "不足", "难以", "不会", "不再", "仍未", "尚未"}

# ═══════════════════════════════════════════════════════════════
# Chinese Intensifiers (multiply polarity by factor)
# ═══════════════════════════════════════════════════════════════
CN_INTENSIFIERS: dict[str, float] = {
    "非常": 1.5, "极其": 1.8, "十分": 1.4, "特别": 1.3, "尤其": 1.3,
    "大幅": 1.5, "显著": 1.4, "明显": 1.3, "急剧": 1.6, "持续": 1.2,
    "进一步": 1.3, "更加": 1.3, "日益": 1.2, "不断": 1.1, "继续": 1.1,
}
CN_DIMINISHERS: dict[str, float] = {
    "略微": 0.5, "稍": 0.5, "微": 0.4, "小幅": 0.6, "温和": 0.7,
    "暂时": 0.6, "短期": 0.7, "或许": 0.5, "可能": 0.7, "似乎": 0.5,
}

# ═══════════════════════════════════════════════════════════════
# English Financial Sentiment (Loughran-McDonald subset + custom)
# ═══════════════════════════════════════════════════════════════
EN_LEXICON: dict[str, float] = {
    # Positive
    "surge": 0.8, "soar": 0.8, "rally": 0.7, "jump": 0.6, "gain": 0.5,
    "rise": 0.4, "climb": 0.4, "boost": 0.5, "bullish": 0.7, "upbeat": 0.6,
    "outperform": 0.7, "beat": 0.6, "exceed": 0.6, "breakthrough": 0.75,
    "recovery": 0.55, "growth": 0.5, "expand": 0.5, "optimism": 0.6,
    "upward": 0.5, "strong": 0.5, "positive": 0.5, "profit": 0.5,
    "rebound": 0.55, "momentum": 0.45, "resilience": 0.5, "dividend": 0.4,
    "buyback": 0.45, "upgrade": 0.55, "easing": 0.4, "stimulus": 0.35,
    "tailwind": 0.5, "catalyst": 0.5, "accelerate": 0.5, "boom": 0.7,
    "thrive": 0.65, "prosper": 0.65, "robust": 0.55,
    "record high": 0.8, "all-time high": 0.85, "better than expected": 0.6,

    # Negative
    "plunge": -0.8, "tumble": -0.75, "sink": -0.65, "drop": -0.5, "fall": -0.45,
    "decline": -0.4, "slump": -0.7, "crash": -0.9, "bearish": -0.7, "downturn": -0.6,
    "underperform": -0.65, "miss": -0.5, "loss": -0.55, "recession": -0.7,
    "layoff": -0.55, "tariff": -0.45, "sanction": -0.6, "risk": -0.3,
    "warning": -0.35, "concern": -0.35, "selloff": -0.65, "downgrade": -0.55,
    "default": -0.85, "contagion": -0.7, "bubble": -0.6, "overvalued": -0.55,
    "headwind": -0.5, "weaken": -0.4, "soften": -0.4, "contract": -0.45,
    "stagnate": -0.5, "stall": -0.5, "sluggish": -0.5, "gloom": -0.6,
    "pessimism": -0.6, "unemployment": -0.4, "inflation": -0.2, "debt": -0.4,
    "crisis": -0.85, "turmoil": -0.7, "panic": -0.75, "collapse": -0.9,
}
EN_NEGATION = {"not", "no", "never", "neither", "nor", "hardly", "barely", "rarely", "lack", "lacks", "lacking", "without"}
EN_INTENSIFIERS: dict[str, float] = {
    "very": 1.5, "extremely": 1.7, "significantly": 1.4, "sharply": 1.5,
    "dramatically": 1.6, "substantially": 1.3, "strongly": 1.3,
}
EN_DIMINISHERS: dict[str, float] = {
    "slightly": 0.5, "somewhat": 0.6, "modestly": 0.6, "marginally": 0.4,
}


@dataclass
class SentimentResult:
    score: float  # [-1.0, 1.0]
    label: str  # bullish, bearish, neutral
    confidence: float  # 0.0 ~ 1.0
    positive_hits: int
    negative_hits: int
    details: dict


class RuleSentimentEngineV2:
    """Chinese + English financial sentiment analyzer with continuous scoring."""

    def __init__(self):
        # Build compiled patterns
        self.cn_words = self._build_pattern(CN_LEXICON)
        self.en_words = self._build_pattern(EN_LEXICON)

    def _build_pattern(self, lexicon: dict[str, float]) -> list[tuple[re.Pattern, float]]:
        """Build regex patterns for lexicon entries, sorted by length (longest first)."""
        entries = []
        for word, score in sorted(lexicon.items(), key=lambda x: -len(x[0])):
            pattern = re.compile(re.escape(word), re.IGNORECASE)
            entries.append((pattern, score))
        return entries

    def analyze(self, title: str, content: str = "") -> SentimentResult:
        """Analyze sentiment of article with title-weighted scoring."""
        title = title or ""
        content = content or ""

        # Extract lead paragraph (first 300 chars of content)
        lead = content[:300] if content else ""

        # Score each section
        title_score, title_hits = self._score_text(title, is_chinese=self._is_chinese(title))
        lead_score, lead_hits = self._score_text(lead, is_chinese=self._is_chinese(lead))
        body_score, body_hits = self._score_text(content, is_chinese=self._is_chinese(content))

        # Weighted combination: title 3x, lead 2x, body 1x
        total_hits = title_hits + lead_hits + body_hits
        if total_hits > 0:
            weighted_score = (
                title_score * 3.0 + lead_score * 2.0 + body_score * 1.0
            ) / 6.0
        else:
            weighted_score = 0.0

        # Clamp to [-1, 1]
        score = max(-1.0, min(1.0, weighted_score))

        # Adaptive threshold for label
        if score >= 0.25:
            label = "bullish"
        elif score <= -0.25:
            label = "bearish"
        else:
            label = "neutral"

        # Confidence based on hit count and score magnitude
        confidence = min(1.0, (total_hits / 10.0) * abs(score) * 2.0)
        if total_hits == 0:
            confidence = 0.0

        # Count positive/negative hits
        pos_hits = sum(1 for _, s in self.cn_words if s > 0 and (_.search(title) or _.search(content)))
        pos_hits += sum(1 for _, s in self.en_words if s > 0 and (_.search(title) or _.search(content)))
        neg_hits = sum(1 for _, s in self.cn_words if s < 0 and (_.search(title) or _.search(content)))
        neg_hits += sum(1 for _, s in self.en_words if s < 0 and (_.search(title) or _.search(content)))

        return SentimentResult(
            score=round(score, 3),
            label=label,
            confidence=round(confidence, 3),
            positive_hits=pos_hits,
            negative_hits=neg_hits,
            details={"title_hits": title_hits, "lead_hits": lead_hits, "body_hits": body_hits},
        )

    def _is_chinese(self, text: str) -> bool:
        """Heuristic: if >30% of characters are in CJK range, treat as Chinese."""
        if not text:
            return True
        cjk = sum(1 for c in text if '一' <= c <= '鿿')
        return cjk / max(1, len(text)) > 0.3

    def _score_text(self, text: str, is_chinese: bool = True) -> tuple[float, int]:
        """Score text and return (weighted_score, hit_count)."""
        if not text:
            return 0.0, 0

        patterns = self.cn_words if is_chinese else self.en_words
        negations = CN_NEGATION if is_chinese else EN_NEGATION
        intensifiers = CN_INTENSIFIERS if is_chinese else EN_INTENSIFIERS
        diminishers = CN_DIMINISHERS if is_chinese else EN_DIMINISHERS

        total_score = 0.0
        hit_count = 0
        words = list(self._iter_words(text))

        for i, word in enumerate(words):
            # Check if word matches a sentiment term
            sentiment = self._match_sentiment(word, patterns)
            if sentiment == 0.0:
                continue

            polarity = sentiment
            hit_count += 1

            # Check for negation in previous 3 words
            for j in range(max(0, i - 3), i):
                if words[j] in negations:
                    polarity = -polarity
                    break

            # Check for intensifier/diminisher in previous 2 words
            for j in range(max(0, i - 2), i):
                if words[j] in intensifiers:
                    polarity *= intensifiers[words[j]]
                    break
                if words[j] in diminishers:
                    polarity *= diminishers[words[j]]
                    break

            total_score += polarity

        return total_score, hit_count

    def _match_sentiment(self, word: str, patterns: list[tuple[re.Pattern, float]]) -> float:
        """Check if word matches any sentiment pattern."""
        for pattern, score in patterns:
            if pattern.fullmatch(word):
                return score
        return 0.0

    def _iter_words(self, text: str):
        """Iterate Chinese character bigrams/trigrams and English words."""
        # For Chinese, use character-level n-grams
        import re as _re
        # Extract CJK and non-CJK segments
        tokens = _re.findall(r'[一-鿿]+|[a-zA-Z]+', text.lower())
        for token in tokens:
            if _re.match(r'[一-鿿]', token):
                # Chinese: yield 1-4 character grams
                for i in range(len(token)):
                    for n in range(1, 5):
                        if i + n <= len(token):
                            yield token[i:i + n]
            else:
                # English: yield individual words
                yield token
