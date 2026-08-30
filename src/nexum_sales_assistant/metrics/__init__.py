"""Métricas operacionais do Nexum Sales Assistant (ADR-007).

As métricas do dashboard são queries SQL sobre as tabelas existentes —
nenhuma nova Gold é criada e os contratos das quatro Golds permanecem
intactos. Cada query declara sua fonte. Os helpers puros em `queries.py`
são a referência testável (dados vazios e divisão segura).
"""

from nexum_sales_assistant.metrics.queries import (
    ALLOWED_TABLES,
    DATASET_QUERIES,
    funnel_counts,
    safe_rate,
)

__all__ = ["ALLOWED_TABLES", "DATASET_QUERIES", "funnel_counts", "safe_rate"]
