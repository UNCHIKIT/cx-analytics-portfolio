"""Generate the TMDL semantic model (tables, relationships, measures) for the CX ops dashboard.

Targets an existing Power BI Project scaffold created by Power BI Desktop
(File > Save as > Power BI Project), so the surrounding format is guaranteed valid.

Usage:
    python src/build_tmdl.py "D:\\cx-analytics-portfolio\\03-ops-dashboard\\powerbi\\CXOps.SemanticModel"

It writes:
    definition/expressions.tmdl          (DataFolder parameter)
    definition/relationships.tmdl        (6 relationships)
    definition/tables/<table>.tmdl       (7 CSV tables + fact + _Measures)
and ensures definition/model.tmdl lists a `ref table` for every table.
"""

from __future__ import annotations

import csv
import re
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DATA_FOLDER = str(DATA).replace("/", "\\")

INT_RE = re.compile(r"^-?\d+$")
FLOAT_RE = re.compile(r"^-?\d*\.\d+([eE][-+]?\d+)?$|^-?\d+[eE][-+]?\d+$")
DATETIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}([ T]\d{2}:\d{2}(:\d{2})?)?$")
BOOL_VALUES = {"true", "false", "True", "False", "TRUE", "FALSE"}

M_TYPE = {"int64": "Int64.Type", "double": "type number", "boolean": "type logical",
          "dateTime": "type datetime", "string": "type text"}

# explicit overrides where inference would be ambiguous
TYPES: dict[str, str] = {}

OVERRIDES = {
    "date_key": "int64",        # yyyymmdd, must stay an integer key
    "week_index": "int64",
    "csat_score": "int64",      # 1-5 Likert (pandas writes 4.0 because of nulls)
    "ces_score": "int64",       # 1-7
    "nps_score": "int64",       # 0-10
}


def infer_types(path: Path, sample: int = 500) -> dict[str, str]:
    """Derive each column's TMDL data type from the values actually in the CSV."""
    with path.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.reader(fh))[: sample + 1]
    header, body = rows[0], rows[1:]
    types: dict[str, str] = {}
    for i, col in enumerate(header):
        values = [r[i].strip() for r in body if i < len(r) and r[i].strip() != ""]
        if not values:
            types[col] = "string"
            continue
        if col in OVERRIDES:
            types[col] = OVERRIDES[col]
        elif all(v in BOOL_VALUES for v in values):
            types[col] = "boolean"
        elif all(INT_RE.match(v) for v in values):
            types[col] = "int64"
        elif all(INT_RE.match(v) or FLOAT_RE.match(v) for v in values):
            types[col] = "double"
        elif all(DATETIME_RE.match(v) for v in values):
            types[col] = "dateTime"
        else:
            types[col] = "string"
    return types


def data_type(column: str) -> str:
    """Kept for the M partition builder: names are resolved through TYPES first."""
    return TYPES.get(column, "string")


# ---------------------------------------------------------------- table metadata

# columns hidden from report view
HIDDEN = {
    "fact_interaction": {"case_id", "customer_id", "agent_id", "channel_id", "queue_id",
                         "date_key", "contact_seq", "case_contact_count", "sla_target_seconds",
                         "unit_cost_mop", "is_closing_contact"},
    "dim_date": {"date_key"},
    "dim_channel": {"channel_id", "unit_cost_mop"},
    "dim_queue": {"queue_id", "satisfaction_offset"},
    "dim_agent": {"agent_id"},
    "dim_customer": {"customer_id"},
    "dim_status": set(),
    "_Measures": {"_"},
}

# primary key columns (isKey) per dimension
KEYS = {"dim_date": "date_key", "dim_channel": "channel_id", "dim_queue": "queue_id",
        "dim_agent": "agent_id", "dim_customer": "customer_id", "dim_status": "status"}

# relationships: (from table/column, to table/column)
RELATIONSHIPS = [
    ("fact_interaction", "date_key", "dim_date", "date_key"),
    ("fact_interaction", "channel_id", "dim_channel", "channel_id"),
    ("fact_interaction", "queue_id", "dim_queue", "queue_id"),
    ("fact_interaction", "agent_id", "dim_agent", "agent_id"),
    ("fact_interaction", "customer_id", "dim_customer", "customer_id"),
    ("fact_interaction", "status", "dim_status", "status"),
]

# calculated columns: name -> (dax, data type, hidden)
CALC_COLUMNS = {
    "fact_interaction": [
        ("is_closing_contact",
         "fact_interaction[contact_seq] = fact_interaction[case_contact_count]",
         "boolean", True),
        ("Open age days (live)",
         "IF ( fact_interaction[is_open], DATEDIFF ( fact_interaction[start_ts], TODAY (), DAY ) )",
         "int64", False),
    ]
}

# ---------------------------------------------------------------- measures
# (display folder, name, DAX on one line, format string)
MEASURES = [
    ("Volume", "Contacts", "COUNTROWS ( fact_interaction )", "#,##0"),
    ("Volume", "Cases", "DISTINCTCOUNT ( fact_interaction[case_id] )", "#,##0"),
    ("Volume", "Contacts per case", "DIVIDE ( [Contacts], [Cases] )", "0.00"),
    ("Volume", "Answered contacts", "CALCULATE ( [Contacts], fact_interaction[is_answered] = TRUE () )", "#,##0"),
    ("Volume", "Abandoned contacts", "CALCULATE ( [Contacts], fact_interaction[is_abandoned] = TRUE () )", "#,##0"),
    ("Volume", "Closing contacts", "CALCULATE ( [Contacts], fact_interaction[is_closing_contact] = TRUE () )", "#,##0"),
    ("Volume", "Responded surveys", "CALCULATE ( [Contacts], fact_interaction[responded] = TRUE () )", "#,##0"),
    ("Volume", "Abandonment %", "DIVIDE ( [Abandoned contacts], [Contacts] )", "0.0%"),
    ("Volume", "Repeat contact %", "DIVIDE ( CALCULATE ( [Contacts], fact_interaction[contact_seq] > 1 ), [Contacts] )", "0.0%"),

    ("Service level", "SLA %", "DIVIDE ( CALCULATE ( [Contacts], fact_interaction[is_within_sla] = TRUE () ), [Answered contacts] )", "0.0%"),
    ("Service level", "ASA seconds", "CALCULATE ( AVERAGE ( fact_interaction[wait_seconds] ), dim_channel[is_synchronous] = TRUE (), fact_interaction[is_answered] = TRUE () )", "#,##0"),
    ("Service level", "First response hours", "CALCULATE ( DIVIDE ( AVERAGE ( fact_interaction[wait_seconds] ), 3600 ), dim_channel[is_synchronous] = FALSE (), fact_interaction[is_answered] = TRUE () )", "0.0 \"h\""),
    ("Service level", "AHT seconds", "CALCULATE ( AVERAGE ( fact_interaction[handle_seconds] ), fact_interaction[is_answered] = TRUE () )", "#,##0"),
    ("Service level", "AHT minutes", "DIVIDE ( [AHT seconds], 60 )", "0.0"),

    ("Resolution", "FCR %", "DIVIDE ( CALCULATE ( DISTINCTCOUNT ( fact_interaction[case_id] ), fact_interaction[is_first_contact_resolved] = TRUE () ), [Cases] )", "0.0%"),
    ("Resolution", "Escalation %", "DIVIDE ( CALCULATE ( DISTINCTCOUNT ( fact_interaction[case_id] ), fact_interaction[is_escalated] = TRUE () ), [Cases] )", "0.0%"),
    ("Resolution", "Avg transfers", "CALCULATE ( AVERAGE ( fact_interaction[transfer_count] ), fact_interaction[is_answered] = TRUE () )", "0.00"),

    ("Experience", "Response rate %", "DIVIDE ( [Responded surveys], [Closing contacts] )", "0.0%"),
    ("Experience", "CSAT top-box %", "DIVIDE ( CALCULATE ( [Contacts], fact_interaction[csat_score] >= 4 ), [Responded surveys] )", "0.0%"),
    ("Experience", "CSAT mean", "CALCULATE ( AVERAGE ( fact_interaction[csat_score] ), fact_interaction[responded] = TRUE () )", "0.00"),
    ("Experience", "CES mean", "CALCULATE ( AVERAGE ( fact_interaction[ces_score] ), fact_interaction[responded] = TRUE () )", "0.00"),
    ("Experience", "CES % easy", "DIVIDE ( CALCULATE ( [Contacts], fact_interaction[ces_score] >= 5 ), [Responded surveys] )", "0.0%"),
    ("Experience", "Promoters", "CALCULATE ( [Contacts], fact_interaction[responded] = TRUE (), fact_interaction[nps_score] >= 9 )", "#,##0"),
    ("Experience", "Passives", "CALCULATE ( [Contacts], fact_interaction[responded] = TRUE (), fact_interaction[nps_score] >= 7 && fact_interaction[nps_score] <= 8 )", "#,##0"),
    ("Experience", "Detractors", "CALCULATE ( [Contacts], fact_interaction[responded] = TRUE (), fact_interaction[nps_score] <= 6 )", "#,##0"),
    ("Experience", "NPS", "DIVIDE ( [Promoters] - [Detractors], [Responded surveys] ) * 100", "+0;-0;0"),

    ("Cost", "Cost per contact", "DIVIDE ( SUM ( fact_interaction[cost_mop] ), [Contacts] )", "\"MOP \" #,##0.00"),
    ("Cost", "Cost per case", "DIVIDE ( SUM ( fact_interaction[cost_mop] ), [Cases] )", "\"MOP \" #,##0.00"),
    ("Cost", "Total cost", "SUM ( fact_interaction[cost_mop] )", "\"MOP \" #,##0"),

    ("Backlog", "Open backlog", "CALCULATE ( [Contacts], fact_interaction[is_open] = TRUE () )", "#,##0"),
    ("Backlog", "Oldest open days", "CALCULATE ( MAX ( fact_interaction[age_days] ), fact_interaction[is_open] = TRUE () )", "#,##0"),
    ("Backlog", "Backlog older than 7 days", "CALCULATE ( [Contacts], fact_interaction[is_open] = TRUE (), FILTER ( fact_interaction, DATEDIFF ( fact_interaction[start_ts], TODAY (), DAY ) > 7 ) )", "#,##0"),

    ("Time intelligence", "SLA % (last 4 weeks)", "CALCULATE ( [SLA %], DATESINPERIOD ( dim_date[date], MAX ( dim_date[date] ), -28, DAY ) )", "0.0%"),
    ("Time intelligence", "CSAT mean (last 4 weeks)", "CALCULATE ( [CSAT mean], DATESINPERIOD ( dim_date[date], MAX ( dim_date[date] ), -28, DAY ) )", "0.00"),
    ("Time intelligence", "Contacts 7-day average", "AVERAGEX ( DATESINPERIOD ( dim_date[date], MAX ( dim_date[date] ), -7, DAY ), [Contacts] )", "#,##0"),
    ("Time intelligence", "Contacts vs previous week", "VAR CurrentWeek = [Contacts] VAR PrevWeek = CALCULATE ( [Contacts], DATEADD ( dim_date[date], -7, DAY ) ) RETURN DIVIDE ( CurrentWeek - PrevWeek, PrevWeek )", "+0.0%;-0.0%;0.0%"),
]


# ---------------------------------------------------------------- TMDL emission

def t() -> str:
    return "\t"


def guid() -> str:
    return str(uuid.uuid4())


def q(name: str) -> str:
    """TMDL object name, single-quoted when it contains spaces or special characters."""
    return name if (name.isidentifier() and " " not in name) else "'" + name.replace("'", "''") + "'"


def csv_header(path: Path) -> list[str]:
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return next(csv.reader(fh))


def m_partition(table: str, columns: list[str]) -> list[str]:
    typed = ",\n".join(
        f'{t() * 5}{{"{c}", {M_TYPE[data_type(c)]}}}' for c in columns
    )
    return [
        f"{t()}partition {table} = m",
        f"{t() * 2}mode: import",
        f"{t() * 2}source =",
        f"{t() * 3}let",
        f'{t() * 4}Source = Csv.Document(File.Contents(DataFolder & "\\{table}.csv"), '
        f'[Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),',
        f"{t() * 4}Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),",
        f"{t() * 4}Typed = Table.TransformColumnTypes(Promoted, {{",
        typed,
        f"{t() * 4}}})",
        f"{t() * 3}in",
        f"{t() * 4}Typed",
    ]


def table_tmdl(table: str, columns: list[str]) -> str:
    lines = [f"table {table}", f"{t()}lineageTag: {guid()}", ""]
    for c in columns:
        dt = data_type(c)
        lines.append(f"{t()}column {q(c)}")
        lines.append(f"{t() * 2}dataType: {dt}")
        if c in HIDDEN.get(table, set()):
            lines.append(f"{t() * 2}isHidden")
        if KEYS.get(table) == c:
            lines.append(f"{t() * 2}isKey")
        lines.append(f"{t() * 2}lineageTag: {guid()}")
        summarize = "sum" if dt in ("int64", "double") else "none"
        lines.append(f"{t() * 2}summarizeBy: {summarize}")
        lines.append(f"{t() * 2}sourceColumn: {c}")
        lines.append("")

    for name, dax, dt, hidden in CALC_COLUMNS.get(table, []):
        lines.append(f"{t()}column {q(name)} = {dax}")
        lines.append(f"{t() * 2}dataType: {dt}")
        if hidden:
            lines.append(f"{t() * 2}isHidden")
        lines.append(f"{t() * 2}lineageTag: {guid()}")
        lines.append(f"{t() * 2}summarizeBy: none")
        lines.append("")

    if table == "_Measures":
        lines.append(f"{t()}measure _placeholder = \"\"")
        lines.append(f"{t() * 2}isHidden")
        lines.append("")

    lines.extend(m_partition(table, columns))
    return "\n".join(lines) + "\n"


def measures_tmdl() -> str:
    cols = ["_"]
    lines = [f"table _Measures", f"{t()}lineageTag: {guid()}", "",
             f"{t()}column _", f"{t() * 2}dataType: string", f"{t() * 2}isHidden",
             f"{t() * 2}lineageTag: {guid()}", f"{t() * 2}summarizeBy: none",
             f"{t() * 2}sourceColumn: _", ""]
    for folder, name, dax, fmt in MEASURES:
        lines.append(f"{t()}measure {q(name)} = {dax}")
        lines.append(f"{t() * 2}formatString: {fmt}")
        lines.append(f"{t() * 2}displayFolder: {folder}")
        lines.append(f"{t() * 2}lineageTag: {guid()}")
        lines.append("")
    lines += [
        f"{t()}partition _Measures = m",
        f"{t() * 2}mode: import",
        f"{t() * 2}source =",
        f"{t() * 3}let",
        f'{t() * 4}Source = #table({{"_"}}, {{{{"measures"}}}})',
        f"{t() * 3}in",
        f"{t() * 4}Source",
    ]
    return "\n".join(lines) + "\n"


def expressions_tmdl() -> str:
    return (f'expression DataFolder = "{DATA_FOLDER}" '
            f'meta [IsParameterQuery = true, Type = "Text", IsParameterQueryRequired = true]\n')


def relationships_tmdl() -> str:
    blocks = []
    for ft, fc, tt, tc in RELATIONSHIPS:
        blocks.append("\n".join([
            f"relationship {guid()}",
            f"{t()}fromColumn: {ft}.{fc}",
            f"{t()}toColumn: {tt}.{tc}",
        ]))
    return "\n\n".join(blocks) + "\n"


def update_model_refs(model_file: Path, tables: list[str]) -> str:
    text = model_file.read_text(encoding="utf-8") if model_file.exists() else "model Model\n"
    missing = [tb for tb in tables if f"ref table {tb}" not in text]
    if missing:
        text = text.rstrip() + "\n\n" + "\n".join(f"ref table {tb}" for tb in missing) + "\n"
    # a _Measures table (no data source) also needs no culture gymnastics
    model_file.write_text(text, encoding="utf-8")
    return text


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    model_dir = Path(sys.argv[1])
    definition = model_dir / "definition"
    if not definition.exists():
        print(f"ERROR: {definition} not found. Save the project in Power BI Desktop first.")
        return 1

    (definition / "tables").mkdir(exist_ok=True)

    tables = ["fact_interaction", "dim_date", "dim_channel", "dim_queue",
              "dim_agent", "dim_customer", "dim_status"]
    written = []
    global TYPES
    for tb in tables:
        header = csv_header(DATA / f"{tb}.csv")
        TYPES = infer_types(DATA / f"{tb}.csv")
        (definition / "tables" / f"{tb}.tmdl").write_text(table_tmdl(tb, header), encoding="utf-8")
        types_used = sorted({TYPES[c] for c in header})
        written.append(f"{tb} ({len(header)} cols: {', '.join(types_used)})")

    (definition / "tables" / "_Measures.tmdl").write_text(measures_tmdl(), encoding="utf-8")
    written.append(f"_Measures ({len(MEASURES)} measures)")

    (definition / "expressions.tmdl").write_text(expressions_tmdl(), encoding="utf-8")
    (definition / "relationships.tmdl").write_text(relationships_tmdl(), encoding="utf-8")

    model_file = definition / "model.tmdl"
    update_model_refs(model_file, tables + ["_Measures"])

    print("wrote:")
    for w in written:
        print("  ", w)
    print("  expressions.tmdl (DataFolder parameter)")
    print("  relationships.tmdl (6 relationships)")
    print("  model.tmdl refs updated")
    return 0


if __name__ == "__main__":
    sys.exit(main())

