"""Knowledge Graph API."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.graph import get_graph_stats, get_node_articles, get_visual_data

router = APIRouter()


@router.get("/graph/visual")
def graph_visual(
    node_types: str = Query(""),
    min_weight: float = Query(0.1),
    max_nodes: int = Query(500),
    db: Session = Depends(get_db),
):
    types = [t.strip() for t in node_types.split(",") if t.strip()] if node_types else None
    return get_visual_data(db, node_types=types, min_weight=min_weight, max_nodes=max_nodes)


@router.get("/graph/nodes")
def graph_nodes(
    node_type: str = Query(""),
    min_mentions: int = Query(0),
    page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    from app.models import KGNode
    q = db.query(KGNode)
    if node_type:
        q = q.filter(KGNode.node_type == node_type)
    if min_mentions:
        q = q.filter(KGNode.mention_count >= min_mentions)
    total = q.count()
    nodes = q.order_by(KGNode.importance_score.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {
        "list": [{"id": str(n.id), "nodeType": n.node_type, "name": n.canonical_name,
                   "mentionCount": n.mention_count, "importanceScore": n.importance_score}
                  for n in nodes],
        "total": total, "page": page, "pageSize": page_size,
    }


@router.get("/graph/nodes/{node_id}")
def graph_node_detail(node_id: str, db: Session = Depends(get_db)):
    return get_node_articles(db, node_id)


@router.get("/graph/stats")
def graph_stats(db: Session = Depends(get_db)):
    return get_graph_stats(db)
