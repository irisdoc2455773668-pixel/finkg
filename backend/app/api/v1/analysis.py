"""Analysis results API — keywords, topics, clusters, co-occurrence."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db

router = APIRouter()


@router.get("/analysis/keywords")
def analysis_keywords(top_n: int = Query(50), db: Session = Depends(get_db)):
    try:
        from app.services.nlp.engine import NLPEngine
        nlp = NLPEngine(db.get_bind())
        nlp._load_articles()
        if nlp.article_count == 0:
            return {"ok": True, "keywords": [], "hint": "No articles yet"}
        kw_data = nlp.extract_keywords()
        return {"ok": True, "keywords": kw_data.get("_global", [])[:top_n],
                "articleCount": nlp.article_count}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/analysis/topics")
def analysis_topics(n_topics: int = Query(8), db: Session = Depends(get_db)):
    try:
        from app.services.nlp.engine import NLPEngine
        nlp = NLPEngine(db.get_bind())
        nlp._load_articles()
        topics = nlp.build_lda_topics(n_topics)
        return {"ok": True, "topics": topics}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/analysis/clusters")
def analysis_clusters(n_clusters: int = Query(6), db: Session = Depends(get_db)):
    try:
        from app.services.nlp.engine import NLPEngine
        nlp = NLPEngine(db.get_bind())
        nlp._load_articles()
        clusters = nlp.build_event_clusters(n_clusters)
        return {"ok": True, "clusters": clusters}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/analysis/cooccurrence")
def analysis_cooccurrence(top_n: int = Query(20), db: Session = Depends(get_db)):
    try:
        from app.services.nlp.engine import NLPEngine
        from app.models import KGNode
        nlp = NLPEngine(db.get_bind())
        nlp._load_articles()
        edges = nlp.compute_cooccurrence() if hasattr(nlp, 'compute_cooccurrence') else []
        return {"ok": True, "cooccurrence": edges[:top_n]}
    except Exception as e:
        return {"ok": False, "error": str(e)}
