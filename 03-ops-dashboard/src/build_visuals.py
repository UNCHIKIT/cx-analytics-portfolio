"""Generate the MVP report page (PBIR) for the CX ops dashboard.

Writes visual JSON into an existing PBIR report folder created by Power BI Desktop,
and renames the first page. Safe to re-run: it rewrites the same visual files.

Usage:
    python src/build_visuals.py "D:\\cx-analytics-portfolio\\03-ops-dashboard\\powerbi\\CXOps.Report"

Page layout (1920x1080):
    row 1 : six KPI cards
    row 2 : contacts-vs-SLA combo chart | CSAT by queue bar chart
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.12.0/schema.json"
PAGE_NAME = "Service operations | 服務營運"


def measure(entity: str, name: str) -> dict:
    return {
        "field": {"Measure": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": name}},
        "queryRef": f"{entity}.{name}",
        "nativeQueryRef": name,
    }


def column(entity: str, name: str) -> dict:
    return {
        "field": {"Column": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": name}},
        "queryRef": f"{entity}.{name}",
        "nativeQueryRef": name,
    }


def literal(value: str) -> dict:
    return {"expr": {"Literal": {"Value": value}}}


def visual(name: str, vtype: str, x: int, y: int, w: int, h: int,
           state: dict, title: str | None = None, z: int = 0) -> dict:
    obj: dict = {
        "$schema": SCHEMA,
        "name": name,
        "position": {"x": x, "y": y, "z": z, "width": w, "height": h, "tabOrder": z},
        "visual": {
            "visualType": vtype,
            "query": {"queryState": state},
            "drillFilterOtherVisuals": True,
        },
    }
    if title:
        obj["visual"]["visualContainerObjects"] = {
            "title": [{"properties": {
                "show": literal("true"),
                "text": literal(f"'{title}'"),
                "fontSize": literal("12"),
            }}]
        }
    return obj


def write_visual(page_dir: Path, payload: dict) -> None:
    vdir = page_dir / "visuals" / payload["name"]
    vdir.mkdir(parents=True, exist_ok=True)
    (vdir / "visual.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                                      encoding="utf-8")


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    report_dir = Path(sys.argv[1])
    pages_dir = report_dir / "definition" / "pages"
    pages = sorted(p for p in pages_dir.iterdir() if p.is_dir())
    if not pages:
        print(f"ERROR: no page folder under {pages_dir}")
        return 1
    page_dir = pages[0]

    # rename the page
    page_file = page_dir / "page.json"
    page = json.loads(page_file.read_text(encoding="utf-8"))
    page["displayName"] = PAGE_NAME
    page_file.write_text(json.dumps(page, ensure_ascii=False, indent=2), encoding="utf-8")

    cards = [
        ("Contacts", "Contacts", "#,##0"),
        ("SLA attainment", "SLA %", "0.0%"),
        ("First contact resolution", "FCR %", "0.0%"),
        ("AHT (minutes)", "AHT minutes", "0.0"),
        ("CSAT top-box", "CSAT top-box %", "0.0%"),
        ("NPS", "NPS", "+0;-0;0"),
    ]
    card_w, card_h, gap, left, top = 300, 140, 15, 20, 20
    z = 100
    for i, (label, m, _fmt) in enumerate(cards):
        write_visual(page_dir, visual(
            name=f"v_card_{i}",
            vtype="card",
            x=left + i * (card_w + gap), y=top, w=card_w, h=card_h,
            state={"Values": {"projections": [measure("_Measures", m)]}},
            title=label,
            z=z))
        z += 10

    write_visual(page_dir, visual(
        name="v_combo_weekly",
        vtype="lineClusteredColumnComboChart",
        x=20, y=180, w=1180, h=470,
        state={
            "Category": {"projections": [column("dim_date", "week_start_date")]},
            "Y": {"projections": [measure("_Measures", "Contacts")]},
            "Y2": {"projections": [measure("_Measures", "SLA %")]},
        },
        title="Contacts (column) vs SLA attainment (line) by week",
        z=z))
    z += 10

    write_visual(page_dir, visual(
        name="v_bar_queue_csat",
        vtype="barChart",
        x=1220, y=180, w=680, h=470,
        state={
            "Category": {"projections": [column("dim_queue", "queue")]},
            "Y": {"projections": [measure("_Measures", "CSAT mean")]},
        },
        title="CSAT by service queue",
        z=z))

    print("page renamed to:", PAGE_NAME)
    print("visuals written:", len(cards) + 2)
    for v in sorted((page_dir / "visuals").iterdir()):
        print("  ", v.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
