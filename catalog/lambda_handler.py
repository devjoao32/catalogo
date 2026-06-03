"""Entrada AWS Lambda para executar a API FastAPI via API Gateway."""

from __future__ import annotations

from mangum import Mangum

from catalog.bootstrap import create_app


app = create_app()
handler = Mangum(app, lifespan="off")
