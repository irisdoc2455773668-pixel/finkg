"""NLP analysis pipeline — sentiment, entity extraction, KG construction."""
from __future__ import annotations

import logging
import re
import threading
import time
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import KGEdge, KGNode, KGEntityTimeline, NewsAnalysis, NewsArticle
from app.services.nlp.sentiment.rule_v2 import RuleSentimentEngineV2
from app.utils import shanghai_now
from app.config import settings

logger = logging.getLogger("finkg.analyzer")

# ── Entity extraction patterns (expanded v2) ──

COMPANY_PAT = re.compile(
    r'\b(?:Apple|Google|Microsoft|Amazon|Meta|Tesla|NVIDIA|Nvidia|JPMorgan'
    r'|Goldman\s*Sachs|Morgan\s*Stanley|Bank\s*of\s*America|Citigroup|Wells\s*Fargo'
    r'|BlackRock|Vanguard|Berkshire\s*Hathaway|Exxon|Chevron|Shell|BP|TotalEnergies'
    r'|Pfizer|Johnson\s*&\s*Johnson|UnitedHealth|Walmart|Costco|P&G|Coca-?Cola'
    r'|PepsiCo|McDonald|Starbucks|Nike|Adidas|Toyota|Volkswagen|Samsung|TSMC'
    r'|Intel|AMD|Qualcomm|Broadcom|Oracle|Salesforce|Adobe|Netflix|Disney'
    r'|Comcast|AT&T|Verizon|T-Mobile|OpenAI|Anthropic|Palantir|SpaceX|ByteDance|DeepSeek'
    r'|阿里巴巴|腾讯|百度|京东|拼多多|字节跳动|美团|滴滴|网易|小米|华为'
    r'|比亚迪|宁德时代|工商银行|建设银行|农业银行|中国银行|中国平安|茅台'
    r'|五粮液|中国石油|中国石化|中国移动|中国电信|中国联通|招商银行'
    r'|中信证券|国泰君安|华泰证券|海通证券|兴业银行|浦发银行|交通银行'
    r'|中国神华|长江电力|中芯国际|紫金矿业|格力电器|美的集团|海尔智家'
    r'|隆基绿能|阳光电源|赣锋锂业|天齐锂业|药明康德|恒瑞医药'
    r'|蔚来|理想汽车|小鹏汽车|吉利汽车|长城汽车|长安汽车|广汽集团'
    r'|三一重工|中联重科|海康威视|大疆|商汤科技|科大讯飞|寒武纪|深度求索|月之暗面|智谱'
    r'|蚂蚁集团|微众银行|京东数科|度小满|陆金所)\b', re.IGNORECASE)

LOCATION_PAT = re.compile(
    r'\b(?:United\s*States|China|Japan|Germany|United\s*Kingdom|France|India'
    r'|Brazil|Canada|South\s*Korea|Australia|Russia|EU|European\s*Union'
    r'|ASEAN|Taiwan|Hong\s*Kong|Singapore|Vietnam|Indonesia|Malaysia|Thailand'
    r'|Washington|Beijing|Brussels|London|Tokyo|New\s*York|Shanghai|Shenzhen'
    r'|美国|中国|日本|德国|英国|法国|印度|巴西|加拿大|韩国|澳大利亚|俄罗斯|欧盟'
    r'|东盟|台湾|香港|新加坡|越南|印尼|马来西亚|泰国'
    r'|北京|上海|深圳|广州|杭州|成都|武汉|南京|天津|重庆|香港|台北'
    r'|广东|江苏|浙江|山东|河南|四川|湖北|福建|安徽|河北|湖南'
    r'|欧洲|亚洲|北美|南美|中东|非洲|东南亚|亚太|拉美)\b', re.IGNORECASE)

PERSON_PAT = re.compile(
    r'\b(?:Xi\s*Jinping|Donald\s*Trump|Joe\s*Biden|Jerome\s*Powell|Janet\s*Yellen'
    r'|Elon\s*Musk|Sam\s*Altman|Jensen\s*Huang|Warren\s*Buffett|Larry\s*Fink'
    r'|Christine\s*Lagarde|Vladimir\s*Putin|Emmanuel\s*Macron|Olaf\s*Scholz'
    r'|习近平|李克强|李强|特朗普|拜登|耶伦|鲍威尔|马斯克|黄仁勋|巴菲特'
    r'|马化腾|马云|刘强东|雷军|王传福|曾毓群|任正非|张一鸣|黄峥)\b', re.IGNORECASE)

FINANCE_PAT = re.compile(
    r'\b(?:inflation|CPI|PPI|GDP|PMI|interest\s*rate|Fed|Federal\s*Reserve|ECB'
    r'|PBOC|央行|Treasury|bond|equity|stock|forex|commodity|crypto|Bitcoin'
    r'|tariff|trade\s*war|supply\s*chain|oil\s*price|yield|yields|AI|EV|ESG'
    r'|通胀|利率|央行|美联储|国债|股市|外汇|大宗商品|供应链|关税|脱钩'
    r'|人民币|美元|欧元|日元|英镑|离岸人民币|在岸人民币'
    r'|房地产|新能源|半导体|芯片|人工智能|电动车|光伏|储能|锂电池'
    r'|货币政策|财政政策|降息|加息|降准|LPR|社融|M2|信贷'
    r'|去杠杆|化债|地方债|专项债|城投债|房企'
    r'|量化宽松|缩表|前瞻指引|收益率曲线|利差|信用利差)\b', re.IGNORECASE)

HIGH_RISK = re.compile(
    r'\b(?:crisis|crash|collapse|default|war|sanction|emergency|panic|turmoil|bankruptcy'
    r'|危机|崩盘|违约|战争|制裁|紧急|恐慌|动荡|破产|倒闭|暴雷|爆仓|强平)\b', re.IGNORECASE)
MEDIUM_RISK = re.compile(
    r'\b(?:volatile|uncertain|tension|dispute|probe|investigation|lawsuit|recall'
    r'|波动|不确定|紧张|争端|调查|诉讼|召回|分歧|分歧|僵局)\b', re.IGNORECASE)

# Pipeline state
_pipeline_state: dict = {
    "active": False,
    "stages": [
        {"name": "数据加载", "status": "pending"},
        {"name": "情感分析", "status": "pending"},
        {"name": "实体抽取", "status": "pending"},
        {"name": "节点构建", "status": "pending"},
        {"name": "关系构建", "status": "pending"},
        {"name": "NLP富化", "status": "pending"},
        {"name": "日报生成", "status": "pending"},
    ],
    "progress": 0,
}
_pipeline_lock = threading.Lock()

_sentiment_engine: RuleSentimentEngineV2 | None = None


def get_sentiment_engine() -> RuleSentimentEngineV2:
    global _sentiment_engine
    if _sentiment_engine is None:
        _sentiment_engine = RuleSentimentEngineV2()
    return _sentiment_engine


def get_pipeline_state() -> dict:
    import copy
    with _pipeline_lock:
        return copy.deepcopy(_pipeline_state)


def run_analysis_pipeline(db: Session, date_from: datetime | None = None, date_to: datetime | None = None) -> dict:
    """Process unanalyzed articles in the given time range, generate KG nodes/edges."""
    t0 = time.time()
    engine = get_sentiment_engine()

    with _pipeline_lock:
        _pipeline_state["active"] = True
        _pipeline_state["progress"] = 0
        for s in _pipeline_state["stages"]:
            s["status"] = "pending"

    # Load articles
    q = db.query(NewsArticle).filter(NewsArticle.is_analyzed == False)
    if date_from:
        q = q.filter(NewsArticle.crawled_at >= date_from)
    if date_to:
        q = q.filter(NewsArticle.crawled_at <= date_to)
    articles = q.all()

    if not articles:
        with _pipeline_lock:
            _pipeline_state["active"] = False
            _pipeline_state["stages"][0]["status"] = "done"
        return {"ok": True, "analyzed": 0, "nodes": 0, "edges": 0}

    _update_stage(0, "done")
    total = len(articles)
    analyzed = 0
    node_updates = 0
    new_edges = 0

    # Load existing KG nodes
    existing_nodes: dict[tuple[str, str], KGNode] = {}
    for n in db.query(KGNode).all():
        existing_nodes[(n.node_type, n.canonical_name.lower())] = n

    for i, article in enumerate(articles):
        # Sentiment analysis
        result = engine.analyze(article.title or "", article.content or "")

        # Risk level
        full_text = f"{article.title or ''} {article.content or ''}"
        if HIGH_RISK.search(full_text):
            risk_level, risk_weight = "high", 0.8
        elif MEDIUM_RISK.search(full_text):
            risk_level, risk_weight = "medium", 0.5
        else:
            risk_level, risk_weight = "low", 0.2

        # Entity extraction
        entities: dict[str, list[str]] = {
            "Company": list(set(COMPANY_PAT.findall(full_text)))[:10],
            "Location": list(set(LOCATION_PAT.findall(full_text)))[:8],
            "Person": list(set(PERSON_PAT.findall(full_text)))[:5],
            "FinanceTerm": list(set(FINANCE_PAT.findall(full_text)))[:8],
        }

        # Extract summary
        summary = _extract_summary(article.content or article.title or "")

        # Tags
        tags = ",".join(entities.get("Company", [])[:5] + entities.get("FinanceTerm", [])[:3])

        # Write/update analysis
        existing = db.query(NewsAnalysis).filter(NewsAnalysis.article_id == article.id).first()
        if existing:
            existing.sentiment = result.label
            existing.sentiment_score = result.score
            existing.risk_level = risk_level
            existing.risk_weight = risk_weight
            existing.summary = summary
            existing.tags = tags
            existing.entities = entities
        else:
            db.add(NewsAnalysis(
                article_id=article.id,
                sentiment=result.label,
                sentiment_score=result.score,
                risk_level=risk_level,
                risk_weight=risk_weight,
                summary=summary[:1000],
                tags=tags[:500],
                entities=entities,
                analysis_engine="rule",
            ))

        # Build KG nodes and edges
        art_node = _get_or_create_node(db, existing_nodes, "Article", article.title or f"Article#{article.id}")
        art_node.mention_count = (art_node.mention_count or 0) + 1

        for etype, names in entities.items():
            for name in names:
                target = _get_or_create_node(db, existing_nodes, etype, name)
                target.mention_count = (target.mention_count or 0) + 1
                target.last_seen_at = shanghai_now()
                node_updates += 1

                # Edge: Article mentions Entity
                existing_edge = db.query(KGEdge).filter(
                    KGEdge.source_node_id == art_node.id,
                    KGEdge.target_node_id == target.id,
                    KGEdge.relation_type == "mentions",
                ).first()
                if existing_edge:
                    existing_edge.weight = min(1.0, (existing_edge.weight or 0.5) + 0.1)
                    existing_edge.observation_count = (existing_edge.observation_count or 1) + 1
                    existing_edge.last_observed_at = shanghai_now()
                else:
                    db.add(KGEdge(
                        source_node_id=art_node.id, target_node_id=target.id,
                        relation_type="mentions", weight=0.5,
                    ))
                    new_edges += 1

            # Co-mentioned edges within same type
            e_nodes = [existing_nodes.get((etype, n.lower())) for n in names]
            e_nodes = [n for n in e_nodes if n is not None]
            for i_idx in range(len(e_nodes)):
                for j_idx in range(i_idx + 1, len(e_nodes)):
                    n1, n2 = e_nodes[i_idx], e_nodes[j_idx]
                    if n1.id == n2.id:
                        continue
                    co_edge = db.query(KGEdge).filter(
                        ((KGEdge.source_node_id == n1.id) & (KGEdge.target_node_id == n2.id)) |
                        ((KGEdge.source_node_id == n2.id) & (KGEdge.target_node_id == n1.id)),
                        KGEdge.relation_type == "mentioned_together",
                    ).first()
                    if co_edge:
                        co_edge.weight = min(1.0, (co_edge.weight or 0.3) + 0.05)
                        co_edge.observation_count = (co_edge.observation_count or 1) + 1
                        co_edge.last_observed_at = shanghai_now()
                    else:
                        db.add(KGEdge(
                            source_node_id=n1.id, target_node_id=n2.id,
                            relation_type="mentioned_together", weight=0.3, direction="undirected",
                        ))
                        new_edges += 1

        article.is_analyzed = True
        analyzed += 1
        if i % 50 == 0:
            db.commit()

    db.commit()

    # Update timeline
    _update_stage(1, "done")
    _update_stage(2, "done")
    _update_stage(3, "done")
    _update_stage(4, "done")

    # NLP enrichment (TF-IDF, LDA, KMeans)
    _update_stage(5, "running")
    nlp_stats = {}
    try:
        from app.services.nlp.engine import NLPEngine
        nlp = NLPEngine(db.get_bind())
        nlp_stats = nlp.enrich_kg()
        _update_stage(5, "done")
    except Exception as e:
        logger.warning(f"NLP enrichment failed: {e}")
        _update_stage(5, "done")

    # Narrative sentiment computation
    narrative_stats = {}
    try:
        from app.services.narrative import compute_narrative_sentiment
        narrative_stats = compute_narrative_sentiment(db)
        logger.info(f"Narrative sentiment computed: {narrative_stats.get('rows_upserted', 0)} rows")
    except Exception as e:
        logger.warning(f"Narrative sentiment computation failed: {e}")

    elapsed = round(time.time() - t0, 1)
    logger.info(f"Analysis done: {analyzed} articles in {elapsed}s")
    with _pipeline_lock:
        _pipeline_state["active"] = False
        _pipeline_state["progress"] = 100
    return {"ok": True, "analyzed": analyzed, "nodes": node_updates, "edges": new_edges, "elapsed": elapsed, "nlp": nlp_stats, "narrative": narrative_stats}


def _update_stage(idx: int, status: str):
    with _pipeline_lock:
        if 0 <= idx < len(_pipeline_state["stages"]):
            _pipeline_state["stages"][idx]["status"] = status
        done = sum(1 for s in _pipeline_state["stages"] if s["status"] == "done")
        _pipeline_state["progress"] = round(done / len(_pipeline_state["stages"]) * 100, 1)


def _get_or_create_node(db: Session, existing: dict, node_type: str, name: str) -> KGNode:
    key = (node_type, name.lower())
    if key in existing:
        return existing[key]
    node = KGNode(node_type=node_type, canonical_name=name, mention_count=1, importance_score=0.5)
    db.add(node)
    db.flush()
    existing[key] = node
    return node


def _extract_summary(text: str, max_sentences: int = 2) -> str:
    sents = re.split(r'[。！？.!?\n]', text)
    result = []
    for s in sents:
        s = s.strip()
        if len(s) > 10:
            result.append(s)
        if len(result) >= max_sentences:
            break
    return '。'.join(result) if result else text[:200]
