"""Knowledge graph service — build, query, analyze."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.models import KGEdge, KGNode

logger = logging.getLogger("finkg.graph")


def get_visual_data(db: Session, node_types: list[str] | None = None,
                    min_weight: float = 0.1, max_nodes: int = 500) -> dict:
    """Return full graph data for visualization."""
    q = db.query(KGNode).order_by(KGNode.importance_score.desc())
    if node_types:
        q = q.filter(KGNode.node_type.in_(node_types))
    nodes = q.limit(max_nodes).all()
    node_ids = {n.id for n in nodes}

    edges = db.query(KGEdge).filter(
        KGEdge.source_node_id.in_(node_ids),
        KGEdge.target_node_id.in_(node_ids),
        KGEdge.weight >= min_weight,
    ).all()

    return {
        "nodes": [{"id": str(n.id), "nodeType": n.node_type, "name": n.canonical_name,
                    "mentionCount": n.mention_count, "importanceScore": n.importance_score} for n in nodes],
        "edges": [{"sourceNodeId": str(e.source_node_id), "targetNodeId": str(e.target_node_id),
                    "relationType": e.relation_type, "weight": e.weight} for e in edges],
    }


def get_node_articles(db: Session, node_id: str) -> dict:
    """Get articles related to a KG node."""
    from app.models import NewsAnalysis, NewsArticle

    node = db.query(KGNode).filter(KGNode.id == node_id).first()
    if not node:
        return {"node": None, "articles": []}

    # Find via tags
    analyses = db.query(NewsAnalysis).filter(
        NewsAnalysis.tags.contains(node.canonical_name[:20])
    ).limit(20).all()
    article_ids = [a.article_id for a in analyses]

    # Also direct title/content search
    direct = db.query(NewsArticle).filter(
        NewsArticle.title.contains(node.canonical_name[:30])
    ).limit(10).all()

    all_ids = set(str(a.article_id) for a in analyses) | {str(d.id) for d in direct}
    articles = db.query(NewsArticle).filter(NewsArticle.id.in_(list(all_ids)[:20])).all()

    return {
        "node": {"id": str(node.id), "type": node.node_type, "name": node.canonical_name},
        "articles": [{"id": str(a.id), "title": a.title, "source_name": a.source_name, "url": a.url}
                     for a in articles],
    }


def get_graph_stats(db: Session) -> dict:
    """Graph statistics: node types, relation types, top entities, centrality."""
    node_types = {r[0]: r[1] for r in db.execute(text(
        "SELECT node_type, COUNT(*) FROM kg_nodes GROUP BY node_type ORDER BY 2 DESC"
    )).fetchall()}
    rel_types = {}
    for r in db.execute(text(
        "SELECT relation_type, COUNT(*), AVG(weight) FROM kg_edges GROUP BY relation_type ORDER BY 2 DESC"
    )).fetchall():
        rel_types[r[0]] = {"count": r[1], "avgWeight": round(r[2] or 0, 3)}
    top_entities = []
    for r in db.execute(text("""
        SELECT n.id, n.canonical_name, n.node_type, n.mention_count, n.importance_score,
               (SELECT COUNT(*) FROM kg_edges e WHERE e.source_node_id=n.id OR e.target_node_id=n.id) AS deg
        FROM kg_nodes n WHERE n.node_type != 'Article'
        ORDER BY deg DESC, n.importance_score DESC LIMIT 20
    """)).fetchall():
        top_entities.append({
            "id": str(r[0]), "name": r[1], "type": r[2], "mentions": r[3],
            "importance": round(r[4] or 0, 2), "degree": r[5],
        })
    return {
        "nodeTypes": node_types, "relationTypes": rel_types, "topEntities": top_entities,
        "totalNodes": sum(node_types.values()),
        "totalEdges": sum(v["count"] for v in rel_types.values()),
    }
