"""NLP enrichment engine — TF-IDF + LDA + KMeans + co-occurrence for KG."""
from __future__ import annotations

import hashlib
import logging
import os
import pickle
import re
from collections import Counter

import jieba
import numpy as np
from sklearn.cluster import KMeans
from sklearn.decomposition import LatentDirichletAllocation
from sklearn.feature_extraction.text import TfidfVectorizer

logger = logging.getLogger("finkg.nlp.engine")

CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "nlp_cache")

_STOP_WORDS = set("""
的 了 在 是 我 有 和 就 不 人 都 一 一个 上 也 很 到 说 要 去 你
会 着 没有 看 好 自己 这 他 她 它 们 那 些 什么 哪 吗 啊 吧 呢
为 因为 所以 但是 然而 虽然 如果 可以 已经 还 又 再 才 刚 只
把 被 让 给 从 对 与 或 及 之 其 等 而 且 但 以 能 能够 应该
将 会 可能 需要 这个 那个 这些 那些 这里 那里 怎么 怎样 如何
通过 经过 根据 按照 对于 关于 由于 为了 除了 不仅 而且 然后
已经 正在 即将 仍然 一直 总是 经常 通常 表示 认为 指出 强调
亿元 万元 美元 港元 日元 欧元 英镑 人民币 同比 环比 增长 下降
获悉 记者 消息 此前 此外 据悉 周一 周二 周三 周四 周五 周六 周日
新浪 财经 证券 时报 同花顺 东方财富 来源 报道
the to of in and a an is it for on that with as at by from or
this be are was were been have has had not but if so we he she
they its his her my me our us your can will would could should
may about such than then also only more some other all each any
both few most many no very own per say do does did said like
just over into after before between under through during while
which what when where who how up out new now one two first last
also still next well much too just even because although though
""".split())

jieba.setLogLevel(logging.WARNING)


def _tokenize(text: str) -> list[str]:
    text = re.sub(r'[^一-鿿㐀-䶿\w]', ' ', text or '')
    words = jieba.cut(text)
    return [w.strip() for w in words if len(w.strip()) >= 2 and w.strip() not in _STOP_WORDS and not w.strip().isdigit()]


class NLPEngine:
    """TF-IDF + LDA + KMeans + co-occurrence enrichment for the knowledge graph."""

    def __init__(self, engine):
        self.engine = engine
        os.makedirs(CACHE_DIR, exist_ok=True)
        self._articles: list[dict] = []
        self._tokenized: list[list[str]] = []
        self._article_texts: list[str] = []
        self._article_ids: list[int] = []
        self._tfidf_vectorizer: TfidfVectorizer | None = None
        self._tfidf_matrix = None
        self._lda_model: LatentDirichletAllocation | None = None
        self._kmeans_model: KMeans | None = None

    def _load_articles(self, limit: int = 1000):
        from sqlalchemy.orm import Session
        from app.models import NewsArticle
        with Session(self.engine) as s:
            rows = s.query(NewsArticle).filter(NewsArticle.content != "").order_by(
                NewsArticle.crawled_at.desc()).limit(limit).all()
            self._articles = [{"id": r.id, "title": r.title, "content": r.content,
                               "source_name": r.source_name, "category": r.category} for r in rows]
            self._article_ids = [a["id"] for a in self._articles]
            self._article_texts = [f"{a['title']} {a['content']}" for a in self._articles]
            self._tokenized = [_tokenize(t) for t in self._article_texts]
        logger.info(f"NLP: Loaded {len(self._articles)} articles")

    @property
    def article_count(self) -> int:
        return len(self._articles)

    def _cache_key(self) -> str:
        if not self._article_ids:
            return "empty"
        payload = f"v3:{len(self._article_ids)}:{self._article_ids[0]}:{self._article_ids[-1]}"
        return hashlib.md5(payload.encode()).hexdigest()[:12]

    def _load_cache(self, name: str):
        for old in os.listdir(CACHE_DIR):
            if old.startswith(name):
                try:
                    with open(os.path.join(CACHE_DIR, old), "rb") as f:
                        return pickle.load(f)
                except Exception:
                    pass
        return None

    def _save_cache(self, name: str, obj):
        try:
            for old in os.listdir(CACHE_DIR):
                if old.startswith(name):
                    try:
                        os.remove(os.path.join(CACHE_DIR, old))
                    except OSError:
                        pass
        except OSError:
            pass
        try:
            with open(os.path.join(CACHE_DIR, f"{name}_{self._cache_key()}.pkl"), "wb") as f:
                pickle.dump(obj, f)
        except OSError:
            pass

    def extract_keywords(self, top_n: int = 10) -> dict:
        cached = self._load_cache("tfidf_kw")
        if cached and cached.get("_n") == self.article_count:
            return {k: v for k, v in cached.items() if not k.startswith("_")}
        if not self._article_texts:
            self._load_articles()
        if not self._article_texts:
            return {}
        joined = [" ".join(tokens) for tokens in self._tokenized]
        vec = TfidfVectorizer(max_df=0.85, min_df=2, max_features=5000)
        matrix = vec.fit_transform(joined)
        feature_names = vec.get_feature_names_out()
        self._tfidf_vectorizer = vec
        self._tfidf_matrix = matrix
        result: dict = {}
        for i, row in enumerate(matrix):
            scores = zip(feature_names, row.toarray()[0])
            top = [w for w, s in sorted(scores, key=lambda x: -x[1])[:top_n] if s > 0]
            result[str(self._article_ids[i])] = top
        global_sum = np.array(matrix.sum(axis=0)).flatten()
        global_idx = global_sum.argsort()[::-1][:50]
        result["_global"] = [feature_names[j] for j in global_idx if global_sum[j] > 0]
        result["_n"] = self.article_count
        self._save_cache("tfidf_kw", result)
        return result

    def build_lda_topics(self, n_topics: int = 8) -> list[dict]:
        cached = self._load_cache("lda_topics")
        if cached:
            return cached
        if not self._article_texts:
            self._load_articles()
        if len(self._article_texts) < 10:
            return []
        joined = [" ".join(tokens) for tokens in self._tokenized]
        if self._tfidf_vectorizer is None:
            vec = TfidfVectorizer(max_df=0.85, min_df=2, max_features=5000)
            self._tfidf_matrix = vec.fit_transform(joined)
            self._tfidf_vectorizer = vec
        lda = LatentDirichletAllocation(n_components=n_topics, random_state=42, max_iter=10)
        doc_topics = lda.fit_transform(self._tfidf_matrix)
        self._lda_model = lda
        feature_names = self._tfidf_vectorizer.get_feature_names_out()
        topics = []
        for t_idx in range(n_topics):
            top_idx = lda.components_[t_idx].argsort()[::-1][:15]
            top_words = [feature_names[i] for i in top_idx if lda.components_[t_idx][i] > 0.001]
            label = " / ".join(top_words[:3]) if top_words else f"Topic{t_idx + 1}"
            topics.append({
                "topic_id": t_idx, "label": f"主题{t_idx + 1}: {label}",
                "keywords": top_words[:10],
                "article_count": int((doc_topics.argmax(axis=1) == t_idx).sum()),
            })
        self._save_cache("lda_topics", topics)
        return topics

    def build_event_clusters(self, n_clusters: int = 6) -> list[dict]:
        cached = self._load_cache("kmeans_clusters")
        if cached:
            return cached
        if not self._article_texts:
            self._load_articles()
        if len(self._article_texts) < n_clusters:
            return []
        joined = [" ".join(tokens) for tokens in self._tokenized]
        if self._tfidf_matrix is None:
            vec = TfidfVectorizer(max_df=0.85, min_df=2, max_features=5000)
            self._tfidf_matrix = vec.fit_transform(joined)
            self._tfidf_vectorizer = vec
        km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = km.fit_predict(self._tfidf_matrix)
        self._kmeans_model = km
        clusters = []
        for c_idx in range(n_clusters):
            mask = labels == c_idx
            cluster_ids = [str(self._article_ids[i]) for i, m in enumerate(mask) if m]
            centroid = km.cluster_centers_[c_idx]
            top_idx = centroid.argsort()[::-1][:10]
            feature_names = self._tfidf_vectorizer.get_feature_names_out()
            top_words = [feature_names[j] for j in top_idx if centroid[j] > 0.01]
            label = " / ".join(top_words[:3]) if top_words else f"Cluster{c_idx + 1}"
            clusters.append({
                "cluster_id": c_idx, "label": f"事件簇{c_idx + 1}: {label}",
                "keywords": top_words[:10], "article_count": int(mask.sum()),
                "article_ids": cluster_ids,
            })
        self._save_cache("kmeans_clusters", clusters)
        return clusters

    def enrich_kg(self) -> dict:
        self._load_articles()
        if not self._articles:
            return {"ok": True, "message": "No articles", "stats": {}}
        from sqlalchemy.orm import Session
        from app.models import KGEdge, KGNode
        stats = {"topics": 0, "event_clusters": 0, "cooccur_edges": 0}
        with Session(self.engine) as s:
            existing = {(n.node_type, n.canonical_name): n.id for n in s.query(KGNode).all()}
            topics = self.build_lda_topics()
            for t in topics:
                t_node_id = existing.get(("Topic", t["label"]))
                if not t_node_id:
                    tn = KGNode(node_type="Topic", canonical_name=t["label"], mention_count=t["article_count"])
                    s.add(tn)
                    s.flush()
                    t_node_id = tn.id
                    existing[("Topic", t["label"])] = t_node_id
                stats["topics"] += 1
            clusters = self.build_event_clusters()
            for c in clusters:
                c_node_id = existing.get(("EventCluster", c["label"]))
                if not c_node_id:
                    cn = KGNode(node_type="EventCluster", canonical_name=c["label"], mention_count=c["article_count"])
                    s.add(cn)
                    s.flush()
                    c_node_id = cn.id
                    existing[("EventCluster", c["label"])] = c_node_id
                stats["event_clusters"] += 1
            s.commit()
        logger.info(f"NLP enrichment done: {stats}")
        return {"ok": True, "stats": stats}
