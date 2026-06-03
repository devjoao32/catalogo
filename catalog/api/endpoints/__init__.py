"""Routers segmentados da API de catalogo."""

from .catalog import router as catalog_data_router
from .erp import router as erp_router
from .export import router as export_router
from .media import router as media_router
from .representatives import router as representatives_router

__all__ = [
    "catalog_data_router",
    "erp_router",
    "export_router",
    "media_router",
    "representatives_router",
]
