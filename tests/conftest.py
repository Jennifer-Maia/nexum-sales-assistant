"""This file configures pytest, initializes Databricks Connect, and provides fixtures for Spark and loading test data."""

import os, sys, pathlib
from contextlib import contextmanager


try:
    from databricks.connect import DatabricksSession
    from databricks.sdk import WorkspaceClient
    from pyspark.sql import SparkSession
    import pytest
    import json
    import csv
    import os
except ImportError:
    raise ImportError(
        "Test dependencies not found.\n\nRun tests using 'uv run pytest'. See http://docs.astral.sh/uv to learn more about uv."
    )


@pytest.fixture()
def spark() -> SparkSession:
    """Provide a SparkSession fixture for tests.

    Minimal example:
        def test_uses_spark(spark):
            df = spark.createDataFrame([(1,)], ["x"])
            assert df.count() == 1
    """
    return DatabricksSession.builder.getOrCreate()


@pytest.fixture()
def load_fixture(spark: SparkSession):
    """Provide a callable to load JSON or CSV from fixtures/ directory.

    Example usage:

        def test_using_fixture(load_fixture):
            data = load_fixture("my_data.json")
            assert data.count() >= 1
    """

    def _loader(filename: str):
        path = pathlib.Path(__file__).parent.parent / "fixtures" / filename
        suffix = path.suffix.lower()
        if suffix == ".json":
            rows = json.loads(path.read_text())
            return spark.createDataFrame(rows)
        if suffix == ".csv":
            with path.open(newline="") as f:
                rows = list(csv.DictReader(f))
            return spark.createDataFrame(rows)
        raise ValueError(f"Unsupported fixture type for: {filename}")

    return _loader


def _enable_fallback_compute():
    """Enable serverless compute if no compute is specified."""
    conf = WorkspaceClient().config
    if conf.serverless_compute_id or conf.cluster_id or os.environ.get("SPARK_REMOTE"):
        return

    url = "https://docs.databricks.com/dev-tools/databricks-connect/cluster-config"
    print("☁️ no compute specified, falling back to serverless compute", file=sys.stderr)
    print(f"  see {url} for manual configuration", file=sys.stdout)

    os.environ["DATABRICKS_SERVERLESS_COMPUTE_ID"] = "auto"


@contextmanager
def _allow_stderr_output(config: pytest.Config):
    """Temporarily disable pytest output capture."""
    capman = config.pluginmanager.get_plugin("capturemanager")
    if capman:
        with capman.global_and_fixture_disabled():
            yield
    else:
        yield


def pytest_configure(config: pytest.Config):
    """Configure pytest session."""
    with _allow_stderr_output(config):
        _enable_fallback_compute()

        # Initialize Spark session eagerly, so it is available even when
        # SparkSession.builder.getOrCreate() is used. For DB Connect 15+,
        # we validate version compatibility with the remote cluster.
        if hasattr(DatabricksSession.builder, "validateSession"):
            DatabricksSession.builder.validateSession().getOrCreate()
        else:
            DatabricksSession.builder.getOrCreate()


# ---------------------------------------------------------------------------
# Spark fake em memória para os testes unitários das ferramentas.
#
# As ferramentas em src/nexum_sales_assistant/tools/ acessam o Spark somente
# via a função `_spark` de cada módulo. Os testes a substituem por este fake,
# permitindo verificar contratos, transições de estado e auditoria com dados
# de exemplo em memória (sem os CSVs de fixtures/ e sem tabelas reais).
# ---------------------------------------------------------------------------

import re


class FakeRow:
    """Linha retornada por `collect()`; espelha o uso de `asDict()`."""

    def __init__(self, data):
        self._data = data

    def asDict(self):
        return dict(self._data)


def _matches_condition(row, condition):
    """Avalia condições simples do tipo `col = 'v'`, `col IS [NOT] NULL`, unidas por AND."""
    for part in condition.split(" AND "):
        part = part.strip()
        if " IS NOT NULL" in part:
            column = part.split(" IS NOT NULL")[0].strip()
            if row.get(column) is None:
                return False
        elif " IS NULL" in part:
            column = part.split(" IS NULL")[0].strip()
            if row.get(column) is not None:
                return False
        elif " = " in part:
            column, raw_value = part.split(" = ", 1)
            if row.get(column.strip()) != raw_value.strip().strip("'"):
                return False
    return True


def _parse_schema_columns(schema):
    """Extrai os nomes das colunas de um schema em string do Spark.

    Divide em `", "` (vírgula seguida de espaço) para não quebrar tipos
    como `DECIMAL(10,2)`, cuja vírgula interna não é seguida de espaço.
    """
    return [part.strip().split()[0] for part in schema.split(", ")]


class FakeDataFrame:
    """DataFrame fake com o subconjunto usado pelas ferramentas."""

    def __init__(self, spark, rows, condition=None):
        self._spark = spark
        self._rows = rows
        self._condition = condition
        # No Spark, `df.write` é uma propriedade (DataFrameWriter), não um
        # método; espelhamos isso expondo `write` como atributo.
        self.write = self

    def _resolved(self):
        if self._condition is None:
            return self._rows
        return [r for r in self._rows if _matches_condition(r, self._condition)]

    def filter(self, condition):
        return FakeDataFrame(self._spark, self._rows, condition)

    def collect(self):
        return [FakeRow(r) for r in self._resolved()]

    def count(self):
        return len(self._resolved())

    def mode(self, _mode):
        return self

    def saveAsTable(self, name):
        self._spark.tables.setdefault(name, [])
        self._spark.tables[name].extend([dict(r) for r in self._rows])


def _apply_update(tables, statement):
    """Aplica um UPDATE simples (`SET col = 'v'[, col = NULL] WHERE ...`)."""
    match = re.match(
        r"^UPDATE\s+(\w+)\s+SET\s+(.+?)\s+WHERE\s+(.+)$", statement, re.IGNORECASE
    )
    if not match:
        return
    table_name, set_clause, where_clause = match.groups()
    updates = {}
    for assignment in set_clause.split(", "):
        column, raw_value = assignment.split(" = ", 1)
        raw_value = raw_value.strip()
        updates[column.strip()] = None if raw_value.upper() == "NULL" else raw_value.strip("'")
    for row in tables.get(table_name, []):
        if _matches_condition(row, where_clause):
            row.update(updates)


class FakeSpark:
    """Spark em memória com suporte ao subconjunto usado pelas ferramentas."""

    def __init__(self):
        self.tables = {}
        self.sql_log = []

    def table(self, name):
        return FakeDataFrame(self, list(self.tables.get(name, [])))

    def createDataFrame(self, rows, schema=None):
        if schema is None:
            data = [dict(r) for r in rows]
        else:
            columns = _parse_schema_columns(schema)
            data = [dict(zip(columns, r)) for r in rows]
        return FakeDataFrame(self, data)

    def sql(self, statement):
        self.sql_log.append(statement)
        _apply_update(self.tables, statement)
        return FakeDataFrame(self, [])


@pytest.fixture
def fake_spark(monkeypatch):
    """Substitui `_spark` das seis ferramentas por um Spark fake em memória."""
    import importlib

    fake = FakeSpark()
    module_names = [
        "nexum_sales_assistant.tools.search_products",
        "nexum_sales_assistant.tools.check_inventory",
        "nexum_sales_assistant.tools.create_quote",
        "nexum_sales_assistant.tools.request_human_approval",
        "nexum_sales_assistant.tools.simulate_payment",
        "nexum_sales_assistant.tools.generate_document",
    ]
    for module_name in module_names:
        module = importlib.import_module(module_name)
        monkeypatch.setattr(module, "_spark", lambda: fake)
    return fake
