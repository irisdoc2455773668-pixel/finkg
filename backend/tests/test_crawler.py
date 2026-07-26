"""Test crawler utilities."""
from app.utils import content_hash, clean_html


def test_content_hash():
    h1 = content_hash("hello world")
    h2 = content_hash("hello world")
    h3 = content_hash("different")
    assert h1 == h2
    assert h1 != h3
    assert len(h1) == 16


def test_clean_html():
    assert clean_html("<p>Hello</p>") == "Hello"
    assert clean_html("<a href='x'>link</a> text") == "link text"
    assert clean_html("plain text") == "plain text"


def test_category_inference():
    from app.services.crawler import infer_category
    assert infer_category("GDP增长预期上调") == "economy"
    assert infer_category("芯片技术突破") == "technology"
    assert infer_category("某公司IPO上市") == "business"
    assert infer_category("文化交流活动") == "culture"
    assert infer_category("医疗改革方案") == "society"
    assert infer_category("政府工作报告") == "politics"
