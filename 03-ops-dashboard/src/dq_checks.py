"""Data quality checks for the CX ops dataset / model.

The checks mirror the table in docs/data-model.md and are the contract the Power BI model
must not violate. Exit code 1 if any check fails, so this can gate a pipeline refresh.

Run:  python src/dq_checks.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, bool(ok), detail))


def main() -> int:
    fact = pd.read_csv(DATA / "fact_interaction.csv", parse_dates=["start_ts", "end_ts"])
    dims = {n: pd.read_csv(DATA / f"{n}.csv") for n in
            ["dim_date", "dim_channel", "dim_queue", "dim_agent", "dim_customer", "dim_status"]}

    # --- keys and referential integrity -----------------------------------
    dup = int(fact["interaction_id"].duplicated().sum())
    check("interaction_id unique", dup == 0, f"{dup} duplicates")

    for fk, dim, pk in [("date_key", "dim_date", "date_key"),
                        ("channel_id", "dim_channel", "channel_id"),
                        ("queue_id", "dim_queue", "queue_id"),
                        ("agent_id", "dim_agent", "agent_id"),
                        ("customer_id", "dim_customer", "customer_id"),
                        ("status", "dim_status", "status")]:
        orphans = int((~fact[fk].isin(dims[dim][pk])).sum())
        check(f"{fk} -> {dim}.{pk}", orphans == 0, f"{orphans} orphan rows")

    # --- series integrity (case -> contacts) ------------------------------
    n_cases = fact["case_id"].nunique()
    mismatch = fact.groupby("case_id").agg(
        n=("contact_seq", "size"), declared=("case_contact_count", "max"),
        seq_max=("contact_seq", "max")).query("n != declared or seq_max != declared")
    check("contact series complete (seq 1..n == case_contact_count)",
          len(mismatch) == 0, f"{len(mismatch)} of {n_cases} cases inconsistent")

    closers = fact[fact["contact_seq"] == fact["case_contact_count"]].groupby("case_id").size()
    check("exactly one closing contact per case",
          (closers == 1).all() and len(closers) == n_cases,
          f"{int((closers != 1).sum())} cases with != 1 closer")

    fcr_wrong = fact[(fact["is_first_contact_resolved"]) & (fact["contact_seq"] != 1)]
    check("is_first_contact_resolved only on contact 1", len(fcr_wrong) == 0,
          f"{len(fcr_wrong)} rows")

    # --- flag coherence ---------------------------------------------------
    check("responded implies closing contact",
          bool((fact.loc[fact["responded"], "contact_seq"]
                == fact.loc[fact["responded"], "case_contact_count"]).all()))
    check("is_within_sla implies is_answered",
          bool((~fact.loc[fact["is_within_sla"], "is_answered"]).sum() == 0))
    check("is_abandoned implies not answered",
          bool(fact.loc[fact["is_abandoned"], "is_answered"].sum() == 0))
    check("is_abandoned implies status Abandoned",
          set(fact.loc[fact["is_abandoned"], "status"].unique()) <= {"Abandoned"})
    check("is_abandoned implies not open",
          bool(fact.loc[fact["is_abandoned"], "is_open"].sum() == 0))
    check("is_open implies status in {Open, Pending}",
          set(fact.loc[fact["is_open"], "status"].unique()) <= {"Open", "Pending"})
    check("is_repeat_contact == (contact_seq > 1)",
          bool((fact["is_repeat_contact"] == (fact["contact_seq"] > 1)).all()))

    # --- timestamps and ages ---------------------------------------------
    check("end_ts null exactly when open",
          bool(fact["end_ts"].isna().equals(fact["is_open"])))
    check("age_days positive", bool((fact["age_days"] >= 0).all()),
          f"min {fact['age_days'].min()}")
    check("closed contacts end after they start",
          bool((fact.loc[~fact["is_open"], "end_ts"]
                >= fact.loc[~fact["is_open"], "start_ts"]).all()))

    # --- survey value domains --------------------------------------------
    for col, lo, hi in [("csat_score", 1, 5), ("ces_score", 1, 7), ("nps_score", 0, 10)]:
        non_null = fact[col].dropna()
        ok_range = bool(non_null.between(lo, hi).all())
        check(f"{col} within {lo}..{hi}", ok_range, f"{len(non_null):,} values")
        wrong_rows = fact[fact[col].notna() != fact["responded"]]
        check(f"{col} present exactly when responded", len(wrong_rows) == 0,
              f"{len(wrong_rows)} rows off")

    # --- cost -------------------------------------------------------------
    check("cost_mop >= 0 and not null",
          bool(fact["cost_mop"].notna().all() and (fact["cost_mop"] >= 0).all()))

    # --- calendar coverage ------------------------------------------------
    days = fact["start_ts"].dt.normalize().nunique()
    check("exactly 182 covered days", days == 182, f"{days} days")
    check("exactly 26 complete weeks", fact["week_index"].nunique() == 26,
          f"{fact['week_index'].nunique()} weeks")
    check("week_index consistent with start_ts",
          bool(fact["week_index"].equals(((fact["start_ts"] - pd.Timestamp("2026-04-06")).dt.days // 7 + 1).astype(int))))

    # --- report -----------------------------------------------------------
    width = max(len(n) for n, _, _ in results)
    failed = 0
    for name, ok, detail in results:
        mark = "PASS" if ok else "FAIL"
        if not ok:
            failed += 1
        print(f"[{mark}] {name.ljust(width)}  {detail}")
    print(f"\n{len(results) - failed}/{len(results)} checks passed"
          f" | rows={len(fact):,} cases={n_cases:,}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
