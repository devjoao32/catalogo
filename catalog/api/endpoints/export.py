"""Endpoints de exportacao do catalogo."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, Response

from ..errors import internal_server_error_response
from ..security import require_representative_access


router = APIRouter(dependencies=[Depends(require_representative_access)])
logger = logging.getLogger(__name__)


@router.get("/export")
async def export_catalog(
    format: str = "csv",
    query: str | None = None,
    category: str | None = None,
    code: str | None = None,
    brand: str | None = None,
):
    """Gera uma exportacao do catalogo em CSV, Excel, JSON, PDF ou ZIP."""
    try:
        from ...exporter import build_catalog_export

        payload, media_type, filename = build_catalog_export(
            format_name=format,
            query=str(query or "").strip(),
            category=str(category or "").strip(),
            code=str(code or "").strip(),
            brand=str(brand or "").strip(),
        )
        return Response(
            content=payload,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Cache-Control": "no-store",
            },
        )
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})
    except Exception as exc:
        logger.exception("Error exporting catalog: %s", exc)
        return internal_server_error_response()
