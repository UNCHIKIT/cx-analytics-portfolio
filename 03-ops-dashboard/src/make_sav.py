"""Build an SPSS-native survey dataset (.sav) for the CX metrics work.

Why: the role asks for SPSS. This project has no SPSS licence, so instead of faking
SPSS output we ship (a) a real SPSS data file with labels and measure levels, and
(b) .sps syntax that runs against it. Both open in SPSS, PSPP, JASP or jamovi.

Grain: one row per RESPONDED post-contact survey (~4.2k rows), with the operational
context of the case attached, plus derived NPS/CSAT/CES analysis variables.

Run:  python src/make_sav.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pyreadstat

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

# SPSS variable labels (questionnaire-style wording)
LABELS = {
    "case_id": "Case identifier",
    "customer_id": "Customer identifier",
    "channel": "Contact channel",
    "channel_num": "Contact channel (numeric factor for ANOVA)",
    "queue": "Service queue (service line)",
    "queue_num": "Service queue (numeric factor for ANOVA)",
    "team": "Handling team",
    "site": "Agent site",
    "segment": "Customer segment",
    "is_new_customer": "New customer flag",
    "survey_date": "Date of the closing contact",
    "week_index": "Reporting week (1-26)",
    "wait_seconds": "Queue wait / time to first response (seconds)",
    "handle_seconds": "Handle time (seconds)",
    "first_contact_resolution": "Resolved on first contact (1=yes, 0=no)",
    "escalated": "Escalated during the case (1=yes, 0=no)",
    "transfer_count": "Number of transfers",
    "case_contact_count": "Contacts needed for this case",
    "repeat_contact": "Needed more than one contact (1=yes, 0=no)",
    "csat": "CSAT: overall satisfaction (1-5)",
    "ces": "CES: ease of getting the issue handled (1-7)",
    "nps": "NPS: likelihood to recommend (0-10)",
    "csat_top_box": "CSAT top-box: 4 or 5 (1=yes, 0=no)",
    "ces_easy": "CES easy: 5-7 (1=yes, 0=no)",
    "nps_group": "NPS group (1=Detractor, 2=Passive, 3=Promoter)",
    "wait_bucket": "Wait time bucket (1=<1min, 2=1-5min, 3=5-30min, 4=>30min)",
}

VALUE_LABELS = {
    "channel": {"Phone": "Phone", "Email": "Email", "Live Chat": "Live chat",
                "Social Media": "Social media", "Web Form": "Web form"},
    "nps_group": {1: "Detractor (0-6)", 2: "Passive (7-8)", 3: "Promoter (9-10)"},
    "first_contact_resolution": {0: "No", 1: "Yes"},
    "escalated": {0: "No", 1: "Yes"},
    "repeat_contact": {0: "No", 1: "Yes"},
    "csat_top_box": {0: "No", 1: "Yes"},
    "ces_easy": {0: "No", 1: "Yes"},
    "is_new_customer": {0: "No", 1: "Yes"},
    "wait_bucket": {1: "<1 min", 2: "1-5 min", 3: "5-30 min", 4: ">30 min"},
    "channel_num": {1: "Email", 2: "Live Chat", 3: "Phone", 4: "Social Media", 5: "Web Form"},
    "queue_num": {1: "Account Management", 2: "Billing", 3: "Complaints & Escalations",
                  4: "Delivery & Logistics", 5: "Technical Support"},
}

MEASURES = {
    "case_id": "nominal", "customer_id": "nominal",
    "channel": "nominal", "queue": "nominal", "team": "nominal", "site": "nominal",
    "channel_num": "nominal", "queue_num": "nominal",
    "segment": "nominal",
    "is_new_customer": "nominal", "first_contact_resolution": "nominal",
    "escalated": "nominal", "repeat_contact": "nominal", "csat_top_box": "nominal",
    "ces_easy": "nominal", "nps_group": "ordinal", "wait_bucket": "ordinal",
    "week_index": "ordinal",
    "survey_date": "scale", "wait_seconds": "scale", "handle_seconds": "scale",
    "transfer_count": "scale", "case_contact_count": "scale",
    "csat": "ordinal", "ces": "ordinal", "nps": "ordinal",
}


def main() -> int:
    fact = pd.read_csv(DATA / "fact_interaction.csv", parse_dates=["start_ts", "end_ts"])
    ch = pd.read_csv(DATA / "dim_channel.csv")
    q = pd.read_csv(DATA / "dim_queue.csv")
    ag = pd.read_csv(DATA / "dim_agent.csv")
    cu = pd.read_csv(DATA / "dim_customer.csv")

    df = (fact.merge(ch[["channel_id", "channel"]], on="channel_id", how="left")
              .merge(q[["queue_id", "queue"]], on="queue_id", how="left")
              .merge(ag[["agent_id", "team", "site"]], on="agent_id", how="left")
              .merge(cu[["customer_id", "segment", "is_new_customer"]], on="customer_id", how="left"))

    resp = df[df["responded"]].copy()
    resp = resp.sort_values(["case_id"])

    out = pd.DataFrame({
        "case_id": resp["case_id"].astype(int),
        "customer_id": resp["customer_id"].astype(int),
        "channel": resp["channel"],
        "queue": resp["queue"],
        "team": resp["team"],
        "site": resp["site"],
        "segment": resp["segment"],
        "is_new_customer": resp["is_new_customer"].astype(int),
        "survey_date": resp["start_ts"],
        "week_index": resp["week_index"].astype(int),
        "wait_seconds": resp["wait_seconds"].astype(int),
        "handle_seconds": resp["handle_seconds"].astype(int),
        "first_contact_resolution": resp["is_first_contact_resolved"].astype(int),
        "escalated": resp["is_escalated"].astype(int),
        "transfer_count": resp["transfer_count"].astype(int),
        "case_contact_count": resp["case_contact_count"].astype(int),
        "repeat_contact": (resp["case_contact_count"] > 1).astype(int),
        "csat": resp["csat_score"].astype(int),
        "ces": resp["ces_score"].astype(int),
        "nps": resp["nps_score"].astype(int),
    })
    out["csat_top_box"] = (out["csat"] >= 4).astype(int)
    out["ces_easy"] = (out["ces"] >= 5).astype(int)
    out["nps_group"] = pd.cut(out["nps"], [-1, 6, 8, 10], labels=[1, 2, 3]).astype(int)
    out["wait_bucket"] = pd.cut(out["wait_seconds"], [-1, 60, 300, 1800, 10**9],
                                labels=[1, 2, 3, 4]).astype(int)

    # SPSS ANOVA / ordinal regression need NUMERIC factors, not strings
    channel_codes = {name: i + 1 for i, name in enumerate(sorted(out["channel"].unique()))}
    queue_codes = {name: i + 1 for i, name in enumerate(sorted(out["queue"].unique()))}
    out.insert(2, "channel_num", out["channel"].map(channel_codes).astype(int))
    out.insert(4, "queue_num", out["queue"].map(queue_codes).astype(int))

    path = DATA / "cx_survey.sav"
    pyreadstat.write_sav(
        out, str(path),
        file_label="CX post-contact survey (synthetic, 26 weeks) — portfolio piece 03",
        column_labels=[LABELS[c] for c in out.columns],
        variable_value_labels=VALUE_LABELS,
        variable_measure=MEASURES,
    )

    # ---- verify by reading the file back -----------------------------------
    back, meta = pyreadstat.read_sav(str(path))
    print("wrote:", path)
    print("rows x cols:", back.shape)
    print("file label:", meta.file_label)
    print("value labels example (nps_group):", meta.variable_value_labels.get("nps_group"))
    print("measure levels sample:", {k: meta.variable_measure[k]
                                     for k in ("csat", "nps_group", "channel", "wait_seconds")})
    print("column label example (csat):", meta.column_names_to_labels.get("csat"))
    print()
    print("--- SPSS-style verification numbers (must match outputs/kpi_reference.md) ---")
    print(f"NPS            : {(back.nps >= 9).mean() * 100 - (back.nps <= 6).mean() * 100:+.1f}")
    print(f"CSAT top-box % : {back.csat_top_box.mean():.1%}   mean {back.csat.mean():.2f}")
    print(f"CES % easy     : {back.ces_easy.mean():.1%}   mean {back.ces.mean():.2f}")
    print(f"FCR %          : {back.first_contact_resolution.mean():.1%}")
    print(f"Escalation %   : {back.escalated.mean():.1%}")
    print(f"Responses      : {len(back):,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
