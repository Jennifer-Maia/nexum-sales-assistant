"""Gera resources/nexum_sales_metrics.lvdash.json (dashboard Lakeview).

O JSON do dashboard é montado programaticamente para garantir
validade estrutural e embutir a logo (data URI). Fontes: somente
Golds (ADR-008); filtro global de período (ADR-008).
"""

import json
import pathlib

from nexum_sales_assistant.metrics.queries import DATASET_QUERIES

LOGO = pathlib.Path(__file__).parent.parent / "src" / "Nexum.png"

Q = {name: "".join(lines) for name, lines in DATASET_QUERIES.items()}

PARAMS = {
    "keyword": "data_range",
    "displayName": "Período",
    "dataType": "DATE",
    "complexType": "RANGE",
    "defaultSelection": {
        "range": {
            "dataType": "DATE",
            "min": {"value": "now-12M/M"},
            "max": {"value": "now/M"},
        }
    },
}


def dataset(name, display, query, parameters=None):
    entry = {"name": name, "displayName": display, "queryLines": query.split("\n")}
    if parameters:
        entry["parameters"] = [parameters]
    return entry


def counter(name, title, dataset_name, field_name, expression, step_filter=None,
            disaggregated=False, fmt=None, display_name=None):
    query = {
        "datasetName": dataset_name,
        "fields": [{"name": field_name, "expression": expression}],
        "disaggregated": disaggregated,
    }
    if step_filter:
        query["filters"] = [{"expression": step_filter}]
    encoding = {"fieldName": field_name, "displayName": display_name or title}
    if fmt:
        encoding["format"] = fmt
    return {
        "widget": {
            "name": name,
            "queries": [{"name": "main_query", "query": query}],
            "spec": {
                "version": 2,
                "widgetType": "counter",
                "encodings": {"value": encoding},
                "frame": {"showTitle": True, "title": title},
            },
        }
    }


def conversion_counter(name, title, dataset_name):
    """KPI de conversão: dataset de 1 linha/1 coluna, sem filtros —
    o formato mais simples e compatível com o renderer do Lakeview."""
    return {
        "widget": {
            "name": name,
            "queries": [{
                "name": "main_query",
                "query": {
                    "datasetName": dataset_name,
                    "fields": [{"name": "taxa", "expression": "`taxa`"}],
                    "disaggregated": True,
                },
            }],
            "spec": {
                "version": 2,
                "widgetType": "counter",
                "encodings": {
                    "value": {
                        "fieldName": "taxa",
                        "displayName": title,
                        "format": {"type": "number-percent", "decimalPlaces": {"type": "exact", "places": 1}},
                    }
                },
                "frame": {"showTitle": True, "title": title},
            },
        }
    }


def text(name, lines):
    return {"widget": {"name": name, "multilineTextboxSpec": {"lines": lines}}}


def bar(name, title, dataset_name, x_field, y_field, y_display, sort_order=None, color_mappings=None):
    x_scale = {"type": "categorical"}
    if sort_order:
        x_scale["sort"] = {"by": "custom-order", "orderedValues": sort_order}
    encodings = {
        "x": {"fieldName": x_field, "scale": x_scale},
        "y": {"fieldName": y_field, "displayName": y_display, "scale": {"type": "quantitative"}},
    }
    if color_mappings:
        encodings["color"] = {
            "fieldName": x_field,
            "scale": {"type": "categorical", "mappings": color_mappings},
        }
    return {
        "widget": {
            "name": name,
            "queries": [{
                "name": "main_query",
                "query": {
                    "datasetName": dataset_name,
                    "fields": [
                        {"name": x_field, "expression": f"`{x_field}`"},
                        {"name": y_field, "expression": f"SUM(`{y_field}`)" if y_field != "count(*)" else "COUNT(*)"},
                    ],
                    "disaggregated": False,
                },
            }],
            "spec": {
                "version": 3,
                "widgetType": "bar",
                "encodings": encodings,
                "frame": {"showTitle": True, "title": title},
            },
        }
    }


def table(name, title, dataset_name, columns, disaggregated=True):
    fields = [{"name": c, "expression": f"`{c}`"} for c in columns]
    cols = []
    for c in columns:
        if c == "atualizado_em":
            cols.append({"fieldName": c, "displayName": "Última ingestão"})
        elif c == "camada":
            cols.append({"fieldName": c, "displayName": "Camada"})
        elif c == "registros":
            cols.append({"fieldName": c, "displayName": "Registros"})
        elif c == "tabela":
            cols.append({"fieldName": c, "displayName": "Tabela"})
        elif c == "etapa_label":
            cols.append({"fieldName": c, "displayName": "Etapa"})
        elif c == "session_id":
            cols.append({"fieldName": c, "displayName": "Sessão"})
        elif c == "created_at":
            cols.append({"fieldName": c, "displayName": "Quando"})
        elif c == "event_type":
            cols.append({"fieldName": c, "displayName": "Evento"})
        elif c == "tool_name":
            cols.append({"fieldName": c, "displayName": "Ferramenta"})
        elif c == "status":
            cols.append({"fieldName": c, "displayName": "Status"})
        elif c == "duration_ms":
            cols.append({"fieldName": c, "displayName": "Duração (ms)"})
        elif c == "primeira_interacao":
            cols.append({"fieldName": c, "displayName": "Primeira interação"})
        elif c == "interacoes":
            cols.append({"fieldName": c, "displayName": "Interações"})
        elif c == "tokens_entrada":
            cols.append({"fieldName": c, "displayName": "Tokens entrada"})
        elif c == "tokens_saida":
            cols.append({"fieldName": c, "displayName": "Tokens saída"})
        elif c == "custo_estimado":
            cols.append({"fieldName": c, "displayName": "Custo estimado"})
        else:
            cols.append({"fieldName": c, "displayName": c})
    return {
        "widget": {
            "name": name,
            "queries": [{
                "name": "main_query",
                "query": {"datasetName": dataset_name, "fields": fields, "disaggregated": disaggregated},
            }],
            "spec": {
                "version": 2,
                "widgetType": "table",
                "encodings": {"columns": cols},
                "frame": {"showTitle": True, "title": title},
            },
        }
    }


def pie(name, title, dataset_name, color_field):
    return {
        "widget": {
            "name": name,
            "queries": [{
                "name": "main_query",
                "query": {
                    "datasetName": dataset_name,
                    "fields": [
                        {"name": color_field, "expression": f"`{color_field}`"},
                        {"name": "count(*)", "expression": "COUNT(*)"},
                    ],
                    "disaggregated": False,
                },
            }],
            "spec": {
                "version": 3,
                "widgetType": "pie",
                "encodings": {
                    "angle": {"fieldName": "count(*)", "scale": {"type": "quantitative"}},
                    "color": {"fieldName": color_field, "scale": {"type": "categorical"}},
                    "label": {"show": True},
                },
                "frame": {"showTitle": True, "title": title},
            },
        }
    }


def pos(x, y, w, h):
    return {"x": x, "y": y, "width": w, "height": h}


def page(name, display, layout):
    return {
        "name": name,
        "displayName": display,
        "pageType": "PAGE_TYPE_CANVAS",
        "layoutVersion": "GRID_V1",
        "layout": layout,
    }


import base64
import io

from PIL import Image

image = Image.open(LOGO).convert("RGBA")
image.thumbnail((192, 192))
buffer = io.BytesIO()
image.save(buffer, format="PNG", optimize=True)
LOGO_B64 = base64.b64encode(buffer.getvalue()).decode("ascii")

logo_markdown = f"![Nexum](data:image/png;base64,{LOGO_B64})"

datasets = [
    dataset("ds_sessions", "Sessões de conversa (Gold)", Q["ds_sessions"]),
    dataset("ds_funnel", "Funil de vendas (Gold)", Q["ds_funnel"], parameters=PARAMS),
    dataset("ds_conversion_cotacao", "Conversão Sessão → Cotação (Gold)", Q["ds_conversion_cotacao"], parameters=PARAMS),
    dataset("ds_conversion_aprovacao", "Conversão Cotação → Aprovação (Gold)", Q["ds_conversion_aprovacao"], parameters=PARAMS),
    dataset("ds_conversion_pagamento", "Conversão Aprovação → Pagamento (Gold)", Q["ds_conversion_pagamento"], parameters=PARAMS),
    dataset("ds_conversion_documento", "Conversão Pagamento → Documento (Gold)", Q["ds_conversion_documento"], parameters=PARAMS),
    dataset("ds_tool_calls", "Chamadas de ferramenta (Gold)", Q["ds_tool_calls"]),
    dataset("ds_agent_turns", "Atividade do agente (Gold)", Q["ds_agent_turns"]),
    dataset("ds_quality", "Qualidade e segurança (Gold)", Q["ds_quality"]),
    dataset("ds_cost", "Custo por sessão (Gold)", Q["ds_cost"], parameters=PARAMS),
    dataset("ds_update", "Atualização dos dados (Gold)", Q["ds_update"]),
]

NUMBER = {"type": "number"}
PERCENT = {"type": "number-percent"}

funnel_counters = [
    ("kpi-sessoes", "Sessões", "sessoes"),
    ("kpi-cotacoes", "Cotações", "cotacoes"),
    ("kpi-aprovacoes", "Aprovações", "aprovacoes"),
    ("kpi-pagamentos", "Pagamentos simulados", "pagamentos_simulados"),
    ("kpi-documentos", "Documentos simulados", "documentos_simulados"),
]

funil_layout = []
funil_layout.append({"widget": text("logo", [logo_markdown])["widget"], "position": pos(0, 0, 3, 3)})
funil_layout.append({
    "widget": text("funil-titulo", ["# Nexum Sales Assistant"])["widget"],
    "position": pos(3, 0, 9, 1),
})
funil_layout.append({
    "widget": text("funil-subtitulo", ["**Funil de vendas** — métricas reais do fluxo Bronze → Silver → Gold e do agente de IA. Use o filtro de período na página Filtros. Zero indica ausência de dados operacionais."])["widget"],
    "position": pos(3, 1, 9, 2),
})
for index, (name, title, step) in enumerate(funnel_counters[:3]):
    funil_layout.append({
        **counter(name, title, "ds_funnel", "count(*)", "COUNT(*)", step_filter=f"`etapa` = '{step}'", fmt=NUMBER),
        "position": pos(index * 4, 3, 4, 3),
    })
for index, (name, title, step) in enumerate(funnel_counters[3:]):
    funil_layout.append({
        **counter(name, title, "ds_funnel", "count(*)", "COUNT(*)", step_filter=f"`etapa` = '{step}'", fmt=NUMBER),
        "position": pos(index * 6, 6, 6, 3),
    })
conversions = [
    ("kpi-conv-cotacao", "Sessão → Cotação", "ds_conversion_cotacao"),
    ("kpi-conv-aprovacao", "Cotação → Aprovação", "ds_conversion_aprovacao"),
    ("kpi-conv-pagamento", "Aprovação → Pagamento", "ds_conversion_pagamento"),
    ("kpi-conv-documento", "Pagamento → Documento", "ds_conversion_documento"),
]
for index, (name, title, dataset_name) in enumerate(conversions):
    funil_layout.append({
        **conversion_counter(name, title, dataset_name),
        "position": pos(index * 3, 9, 3, 3),
    })
funil_layout.append({
    **bar(
        "grafico-funil",
        "Etapas do funil (ordem do fluxo)",
        "ds_funnel",
        "etapa_label",
        "count(*)",
        "Total",
        sort_order=["Sessões", "Cotações", "Aprovações", "Pagamentos simulados", "Documentos simulados"],
    ),
    "position": pos(0, 12, 12, 5),
})
funil_layout.append({**table("tabela-funil", "Funil detalhado", "ds_funnel", ["etapa_label", "count(*)"], disaggregated=False), "position": pos(0, 17, 12, 5)})

ops_layout = [
    {"widget": text("op-titulo", ["# Operação do agente"])["widget"], "position": pos(0, 0, 12, 1)},
    {**counter("kpi-op-sessoes", "Sessões", "ds_sessions", "countdistinct(session_id)", "COUNT(DISTINCT `session_id`)", fmt=NUMBER), "position": pos(0, 1, 3, 3)},
    {**counter("kpi-op-mensagens", "Mensagens de clientes", "ds_sessions", "sum(message_count)", "SUM(`message_count`)", fmt=NUMBER), "position": pos(3, 1, 3, 3)},
    {**counter("kpi-op-latencia", "Latência média do turno (ms)", "ds_agent_turns", "avg(duration_ms)", "AVG(`duration_ms`)", fmt={"type": "number", "decimalPlaces": {"type": "max", "places": 0}}), "position": pos(6, 1, 3, 3)},
    {**counter("kpi-op-tokens", "Tokens de entrada", "ds_agent_turns", "sum(input_tokens)", "SUM(`input_tokens`)", fmt=NUMBER), "position": pos(9, 1, 3, 3)},
    {**pie("pie-uso-ferramentas", "Uso das ferramentas", "ds_tool_calls", "tool_name"), "position": pos(0, 4, 6, 5)},
    {**bar("bar-latencia-ferramentas", "Latência média por ferramenta (ms)", "ds_tool_calls", "tool_name", "duration_ms", "Latência (ms)"), "position": pos(6, 4, 6, 5)},
    {**table("tabela-atividade", "Atividade recente do agente", "ds_agent_turns", ["created_at", "session_id", "event_type", "tool_name", "status", "duration_ms"]), "position": pos(0, 9, 12, 6)},
]

qualidade_layout = [
    {"widget": text("q-titulo", ["# Qualidade e segurança"])["widget"], "position": pos(0, 0, 12, 1)},
    {**counter("kpi-q-recusas", "Recusas (injeção/segredos)", "ds_quality", "total", "`total`", step_filter="`indicador` = 'recusas'", disaggregated=True, fmt=NUMBER), "position": pos(0, 1, 4, 3)},
    {**counter("kpi-q-bloqueios", "Ferramentas não autorizadas bloqueadas", "ds_quality", "total", "`total`", step_filter="`indicador` = 'bloqueios_ferramenta'", disaggregated=True, fmt=NUMBER), "position": pos(4, 1, 4, 3)},
    {**counter("kpi-q-validacao", "Falhas de validação", "ds_quality", "total", "`total`", step_filter="`indicador` = 'falhas_validacao'", disaggregated=True, fmt=NUMBER), "position": pos(8, 1, 4, 3)},
    {**counter("kpi-q-pendentes", "Aprovações pendentes", "ds_quality", "total", "`total`", step_filter="`indicador` = 'aprovacoes_pendentes'", disaggregated=True, fmt=NUMBER), "position": pos(0, 4, 6, 3)},
    {**counter("kpi-q-rejeicoes", "Rejeições", "ds_quality", "total", "`total`", step_filter="`indicador` = 'rejeicoes'", disaggregated=True, fmt=NUMBER), "position": pos(6, 4, 6, 3)},
    {**bar("bar-qualidade", "Indicadores de qualidade e segurança", "ds_quality", "indicador", "total", "Total", color_mappings=[
        {"value": "aprovacoes_pendentes", "color": "#F2B134"},
        {"value": "falhas_validacao", "color": "#F2B134"},
        {"value": "rejeicoes", "color": "#E26D5A"},
        {"value": "recusas", "color": "#E26D5A"},
        {"value": "bloqueios_ferramenta", "color": "#E26D5A"},
        {"value": "erros_agente", "color": "#E26D5A"},
    ]), "position": pos(0, 7, 12, 5)},
    {"widget": text("q-nota", ["Recusas cobrem tentativas de prompt injection e pedidos de segredos. Pendentes/rejeições são o estado corrente (não filtráveis por período). Documentos bloqueados aparecem como ausência de documentos no funil."])["widget"], "position": pos(0, 12, 12, 2)},
]

custo_layout = [
    {"widget": text("c-titulo", ["# Custo da IA"])["widget"], "position": pos(0, 0, 12, 1)},
    {**counter("kpi-c-tokens-in", "Tokens de entrada", "ds_cost", "sum(tokens_entrada)", "SUM(`tokens_entrada`)", fmt=NUMBER), "position": pos(0, 1, 3, 3)},
    {**counter("kpi-c-tokens-out", "Tokens de saída", "ds_cost", "sum(tokens_saida)", "SUM(`tokens_saida`)", fmt=NUMBER), "position": pos(3, 1, 3, 3)},
    {**counter("kpi-c-tokens-turno", "Tokens por interação", "ds_cost", "avg(tokens_por_interacao)", "AVG(`tokens_por_interacao`)", fmt={"type": "number", "decimalPlaces": {"type": "max", "places": 0}}), "position": pos(6, 1, 3, 3)},
    {**counter("kpi-c-custo", "Custo estimado (não fornecido pela FM API → 0)", "ds_cost", "sum(custo_estimado)", "SUM(`custo_estimado`)", fmt={"type": "number", "decimalPlaces": {"type": "max", "places": 6}}), "position": pos(9, 1, 3, 3)},
    {**table("tabela-custo", "Custo e tokens por sessão (período selecionado)", "ds_cost", ["session_id", "primeira_interacao", "interacoes", "tokens_entrada", "tokens_saida", "custo_estimado"]), "position": pos(0, 4, 12, 6)},
]

atualizacao_layout = [
    {"widget": text("a-titulo", ["# Atualização dos dados"])["widget"], "position": pos(0, 0, 12, 1)},
    {**table("tabela-atualizacao", "Tabelas, registros e última ingestão", "ds_update", ["tabela", "camada", "registros", "atualizado_em"]), "position": pos(0, 1, 12, 8)},
    {"widget": text("a-nota", ["Fonte: gold_data_freshness (ADR-008). `atualizado_em` vem do timestamp de ingestão das camadas Bronze/Silver e de `created_at` das tabelas runtime; as Golds não possuem timestamp próprio (NULL)."])["widget"], "position": pos(0, 9, 12, 2)},
]

filters_page = {
    "name": "filters",
    "displayName": "Filtros",
    "pageType": "PAGE_TYPE_GLOBAL_FILTERS",
    "layoutVersion": "GRID_V1",
    "layout": [
        {
            "widget": {
                "name": "filter-periodo",
                "queries": [
                    {"name": "q_sessions", "query": {"datasetName": "ds_sessions", "fields": [{"name": "first_event_at", "expression": "`first_event_at`"}], "disaggregated": False}},
                    {"name": "q_turns", "query": {"datasetName": "ds_agent_turns", "fields": [{"name": "created_at", "expression": "`created_at`"}], "disaggregated": False}},
                    {"name": "q_tool_calls", "query": {"datasetName": "ds_tool_calls", "fields": [{"name": "created_at", "expression": "`created_at`"}], "disaggregated": False}},
                    {"name": "q_funnel", "query": {"datasetName": "ds_funnel", "parameters": [{"name": "data_range", "keyword": "data_range"}], "disaggregated": False}},
                    {"name": "q_conv_cotacao", "query": {"datasetName": "ds_conversion_cotacao", "parameters": [{"name": "data_range", "keyword": "data_range"}], "disaggregated": False}},
                    {"name": "q_conv_aprovacao", "query": {"datasetName": "ds_conversion_aprovacao", "parameters": [{"name": "data_range", "keyword": "data_range"}], "disaggregated": False}},
                    {"name": "q_conv_pagamento", "query": {"datasetName": "ds_conversion_pagamento", "parameters": [{"name": "data_range", "keyword": "data_range"}], "disaggregated": False}},
                    {"name": "q_conv_documento", "query": {"datasetName": "ds_conversion_documento", "parameters": [{"name": "data_range", "keyword": "data_range"}], "disaggregated": False}},
                    {"name": "q_cost", "query": {"datasetName": "ds_cost", "parameters": [{"name": "data_range", "keyword": "data_range"}], "disaggregated": False}},
                ],
                "spec": {
                    "version": 2,
                    "widgetType": "filter-date-range-picker",
                    "encodings": {
                        "fields": [
                            {"fieldName": "first_event_at", "queryName": "q_sessions"},
                            {"fieldName": "created_at", "queryName": "q_turns"},
                            {"fieldName": "created_at", "queryName": "q_tool_calls"},
                            {"parameterName": "data_range", "queryName": "q_funnel"},
                            {"parameterName": "data_range", "queryName": "q_conv_cotacao"},
                            {"parameterName": "data_range", "queryName": "q_conv_aprovacao"},
                            {"parameterName": "data_range", "queryName": "q_conv_pagamento"},
                            {"parameterName": "data_range", "queryName": "q_conv_documento"},
                            {"parameterName": "data_range", "queryName": "q_cost"},
                        ]
                    },
                    "frame": {"showTitle": True, "title": "Período"},
                },
            },
            "position": pos(0, 0, 4, 2),
        }
    ],
}

dashboard = {
    "datasets": datasets,
    "pages": [
        filters_page,
        page("funil", "Funil de vendas", funil_layout),
        page("operacao", "Operação do agente", ops_layout),
        page("qualidade", "Qualidade e segurança", qualidade_layout),
        page("custo", "Custo", custo_layout),
        page("atualizacao", "Atualização dos dados", atualizacao_layout),
    ],
    "uiSettings": {
        "theme": {
            "canvasBackgroundColor": {"light": "#F7F9FB", "dark": "#0E1322"},
            "widgetBackgroundColor": {"light": "#FFFFFF", "dark": "#161C2E"},
            "widgetBorderColor": {"light": "#FFFFFF", "dark": "#161C2E"},
            "fontColor": {"light": "#0B1520", "dark": "#EDF1F6"},
            "selectionColor": {"light": "#0FA88F", "dark": "#34D1B4"},
            "visualizationColors": [
                "#0FA88F", "#2E5FA3", "#F2B134", "#8A6BD8", "#E26D5A", "#57A6E0", "#9BB8D3"
            ],
            "widgetHeaderAlignment": "LEFT",
        }
    },
}

out = pathlib.Path(__file__).parent.parent / "resources" / "nexum_sales_metrics.lvdash.json"
out.write_text(json.dumps(dashboard, indent=2, ensure_ascii=False), encoding="utf-8")
print("gerado:", out, "| datasets:", len(datasets), "| logo b64:", len(LOGO_B64), "chars")
