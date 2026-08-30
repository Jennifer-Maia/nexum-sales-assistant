"""Agente de vendas IA do Nexum Sales Assistant.

Contrato: docs/specs/agent.md
Arquitetura: docs/adrs/ADR-006-agente-ia-arquitetura-de-execucao.md
"""

from nexum_sales_assistant.agent.agent import Agent
from nexum_sales_assistant.agent.llm_client import LLMClient
from nexum_sales_assistant.agent.tool_registry import TOOL_REGISTRY

__all__ = ["Agent", "LLMClient", "TOOL_REGISTRY"]
