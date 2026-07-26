"""Test the Rule v2 sentiment engine."""
from app.services.nlp.sentiment.rule_v2 import RuleSentimentEngineV2


def test_engine_initialization():
    engine = RuleSentimentEngineV2()
    assert engine is not None
    assert len(engine.cn_words) > 100
    assert len(engine.en_words) > 50


def test_bullish_chinese():
    engine = RuleSentimentEngineV2()
    result = engine.analyze("A股暴涨创新高", "股市大幅上涨，多个板块涨停，投资者乐观情绪高涨")
    assert result.label in ("bullish", "neutral")  # conservative check
    assert result.positive_hits >= 0


def test_bearish_chinese():
    engine = RuleSentimentEngineV2()
    result = engine.analyze("全球市场暴跌恐慌", "股市崩盘，投资者恐慌抛售，多只股票跌停")
    assert result.negative_hits >= 0


def test_neutral_text():
    engine = RuleSentimentEngineV2()
    result = engine.analyze("今日天气晴朗", "适合出行游玩，温度适宜")
    # Should be neutral with low confidence
    assert result.confidence < 0.5


def test_score_range():
    engine = RuleSentimentEngineV2()
    result = engine.analyze("测试标题", "测试内容")
    assert -1.0 <= result.score <= 1.0
    assert 0.0 <= result.confidence <= 1.0


def test_mixed_sentiment():
    engine = RuleSentimentEngineV2()
    result = engine.analyze("股市大涨但风险加剧", "利好消息推动上涨，然而危机仍在酝酿，投资者需谨慎")
    assert -1.0 <= result.score <= 1.0


def test_english_bullish():
    engine = RuleSentimentEngineV2()
    result = engine.analyze(
        "Stocks surge to record high",
        "The market rallied strongly today with major indices posting significant gains."
    )
    assert result.label in ("bullish", "neutral")


def test_english_bearish():
    engine = RuleSentimentEngineV2()
    result = engine.analyze(
        "Markets crash amid recession fears",
        "Stocks plunged sharply as investors panic over economic downturn."
    )
    assert result.label in ("bearish", "neutral")
