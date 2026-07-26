"""Multi-agent report generator — single API call with multi-role system prompt."""
from __future__ import annotations

import json
import logging
from sqlalchemy.orm import Session

from app.services.llm.openai_client import chat_completion

logger = logging.getLogger("finkg.report_agent")

MULTI_AGENT_SYSTEM_PROMPT = """你是一个由四位顶尖专家组成的财经叙事分析团队，请共同撰写一份专业宏观经济日报。你必须严格按照以下四位专家的视角依次分析，最后给出综合结论。

## 报告格式要求

请输出以下结构的报告（用Markdown格式）：

### 执行摘要
（200字以内，包含最重要的发现和核心结论）

### 1. 政经地缘分析 — 政经分析师视角
- 本周期的重大政策变化和地缘政治事件
- 各国政府/央行的政策信号解读
- 制裁、关税、贸易协定的影响评估
- 地缘风险评级和情景推演

### 2. 金融市场分析 — 投行金融分析师视角
- 全球股指、外汇、大宗商品、债券市场表现
- 资金流向和投资者情绪分析
- 行业板块轮动和个股影响
- 风险资产/避险资产配置建议

### 3. 量化数据洞察 — 数据科学家视角
- 关键经济指标（CPI/PPI/GDP/PMI/就业）趋势
- 市场数据统计特征（波动率、相关性、异常检测）
- 媒体情绪量化：正面/负面文章比例、情绪得分分布
- 实体网络分析：最活跃的公司/人物/地区

### 4. 社会人文叙事 — 社会学家视角
- 公众关注焦点和社会情绪变化
- 媒体报道框架分析（哪些叙事在主导舆论）
- 不同地区/文化对同一事件的解读差异
- 长期社会趋势和结构性变化

### 综合展望
- 未来1-4周需要关注的关键事件和指标
- 基准情景、乐观情景、悲观情景的概率评估
- 跨市场、跨资产的联动风险提示

## 分析原则
1. 基于提供的数据和资讯，不做无依据的猜测
2. 遇到数据矛盾时，指出分歧而非强求统一
3. 关键判断需标注信息来源
4. 使用中文撰写，专业术语可保留英文原文
5. 数据引用要精确，百分比变化需标注方向
"""


def generate_ai_report(
    db: Session,
    articles_json: list[dict],
    market_snapshot: dict,
    kg_summary: dict,
    date_range: str = "",
) -> tuple[dict | None, str | None]:
    """Generate a professional multi-agent report using LLM.

    Returns (report_dict, error_message). One of them is always None.
    """
    # Build the user message with all context data
    context_parts = [f"## 分析周期\n{date_range}\n"]

    # Market data summary
    if market_snapshot:
        context_parts.append("## 市场数据快照")
        for cat, items in market_snapshot.items():
            if not items:
                continue
            context_parts.append(f"\n### {cat}")
            for item in items[:8]:
                context_parts.append(
                    f"- {item.get('name', item.get('symbol', '?'))}: "
                    f"{item.get('price', 0):,.2f} "
                    f"({'↑' if item.get('change_pct', 0) >= 0 else '↓'}{abs(item.get('change_pct', 0)):.2f}%)"
                )

    # Articles summary (top 30 to keep context manageable)
    if articles_json:
        context_parts.append(f"\n## 资讯摘要（共{len(articles_json)}篇，以下为代表性样本）\n")
        # Group by sentiment
        bullish = [a for a in articles_json if a.get("sentiment") == "bullish"]
        bearish = [a for a in articles_json if a.get("sentiment") == "bearish"]
        neutral = [a for a in articles_json if a.get("sentiment") not in ("bullish", "bearish")]

        for label, subset in [("看涨信号", bullish), ("看跌信号", bearish), ("中性/其他", neutral)]:
            if not subset:
                continue
            context_parts.append(f"\n### {label}（{len(subset)}篇）")
            for a in subset[:8]:
                tags = a.get("tags", "") or ""
                context_parts.append(f"- [{a.get('category', '')}] {a.get('title', '')[:120]} "
                                    f"| {a.get('source', '')} | {a.get('region', '')} | {tags[:60]}")

    # KG summary
    if kg_summary:
        context_parts.append("\n## 知识图谱洞察")
        if kg_summary.get("topEntities"):
            entities = kg_summary["topEntities"][:10]
            context_parts.append("核心实体: " + ", ".join(
                f"{e['name']}({e['type']}, {e.get('mentions', e.get('degree', '?'))})"
                for e in entities
            ))
        if kg_summary.get("nodeTypes"):
            context_parts.append(f"节点分布: {kg_summary['nodeTypes']}")

    user_message = "\n".join(context_parts)

    messages = [
        {"role": "system", "content": MULTI_AGENT_SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]

    content, usage_or_error = chat_completion(db, messages, temperature=0.7, max_tokens=4096)

    if content is None:
        return None, usage_or_error  # usage_or_error is error message here

    # Parse the Markdown report into structured sections
    report = _parse_markdown_report(content, usage_or_error)
    return report, None


def _parse_markdown_report(md_text: str, usage: dict) -> dict:
    """Parse the LLM-generated Markdown report into structured sections."""
    sections = {
        "executive_summary": "",
        "geopolitics": "",
        "markets": "",
        "data_science": "",
        "sociology": "",
        "outlook": "",
    }

    current_section = None
    current_text: list[str] = []

    for line in md_text.split("\n"):
        line_stripped = line.strip()
        if line_stripped.startswith("### 执行摘要") or line_stripped.startswith("## 执行摘要"):
            if current_section:
                sections[current_section] = "\n".join(current_text).strip()
            current_section = "executive_summary"
            current_text = []
        elif "政经" in line_stripped and ("###" in line_stripped or "##" in line_stripped):
            if current_section:
                sections[current_section] = "\n".join(current_text).strip()
            current_section = "geopolitics"
            current_text = []
        elif "金融" in line_stripped and ("###" in line_stripped or "##" in line_stripped):
            if current_section:
                sections[current_section] = "\n".join(current_text).strip()
            current_section = "markets"
            current_text = []
        elif "数据" in line_stripped and ("###" in line_stripped or "##" in line_stripped):
            if current_section:
                sections[current_section] = "\n".join(current_text).strip()
            current_section = "data_science"
            current_text = []
        elif "社会" in line_stripped and ("###" in line_stripped or "##" in line_stripped):
            if current_section:
                sections[current_section] = "\n".join(current_text).strip()
            current_section = "sociology"
            current_text = []
        elif "展望" in line_stripped and ("###" in line_stripped or "##" in line_stripped):
            if current_section:
                sections[current_section] = "\n".join(current_text).strip()
            current_section = "outlook"
            current_text = []
        elif current_section:
            current_text.append(line)

    if current_section and current_text:
        sections[current_section] = "\n".join(current_text).strip()

    # Extract headline from first heading or first line
    headline = ""
    for line in md_text.split("\n")[:10]:
        if line.startswith("#"):
            headline = line.lstrip("#").strip()
            break
    if not headline:
        headline = md_text.split("\n")[0][:100] if md_text else "AI Macro Report"

    return {
        "headline": headline[:300],
        "executive_summary": sections["executive_summary"] or md_text[:500],
        "sections": {
            "geopolitics": sections["geopolitics"] or "",
            "markets": sections["markets"] or "",
            "data_science": sections["data_science"] or "",
            "sociology": sections["sociology"] or "",
            "outlook": sections["outlook"] or "",
        },
        "raw_markdown": md_text,
        "tokens_used": usage.get("total_tokens", 0),
    }
