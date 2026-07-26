"""Aggregate all v1 API routers."""
from fastapi import APIRouter

from app.api.v1 import status, news, market, graph, report, pipeline, source, analysis, narrative, settings

router = APIRouter(prefix="/api/v1")
router.include_router(pipeline.router, tags=["pipeline"])
router.include_router(status.router, tags=["status"])
router.include_router(news.router, tags=["news"])
router.include_router(market.router, tags=["market"])
router.include_router(graph.router, tags=["graph"])
router.include_router(report.router, tags=["report"])
router.include_router(source.router, tags=["source"])
router.include_router(analysis.router, tags=["analysis"])
router.include_router(narrative.router, tags=["narrative"])
router.include_router(settings.router, tags=["settings"])
