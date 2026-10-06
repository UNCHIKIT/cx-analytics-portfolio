"""Reference KPI implementation for the CX ops dashboard (pandas).

Purpose: define every dashboard metric in plain, testable Python BEFORE writing DAX,
so the Power BI numbers can be validated against this file (outputs/kpi_reference.md).
It also verifies the five planted effects described in generate_data.py.

Run:  python src/kpi_reference.py
"""

from __future__ import annotations

import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "outputs"
AS_OF = pd.Timestamp("2026-10-05")


# --------------------------------------------------------------- statistics
def prop_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float, float]:
    """Proportion with 95% CI (normal approximation)."""
    if n == 0:
        return float("nan"), float("nan"), float("nan")
    p = k / n
    se = math.sqrt(p * (1 - p) / n)
    return p, max(0.0, p - z * se), min(1.0, p + z * se)


def two_prop_z(k1: int, n1: int, k2: int, n2: int) -> tuple[float, float]:
    """Two-proportion z test -> (difference, two-sided p)."""
    p1, p2 = k1 / n1, k2 / n2
    p = (k1 + k2) / (n1 + n2)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    if se == 0:
        return p1 - p2, 1.0
    z = (p1 - p2) / se
    return p1 - p2, math.erfc(abs(z) / math.sqrt(2))


def welch(x1: np.ndarray, x2: np.ndarray) -> tuple[float, float, float]:
    """Welch t-test -> (mean difference, 95% CI half-width, two-sided p)."""
    m1, m2 = np.nanmean(x1), np.nanmean(x2)
    v1, v2 = np.nanvar(x1, ddof=1) / len(x1), np.nanvar(x2, ddof=1) / len(x2)
    se = math.sqrt(v1 + v2)
    diff = m1 - m2
    if se == 0:
        return diff, 0.0, 1.0
    z = diff / se
    return diff, 1.96 * se, math.erfc(abs(z) / math.sqrt(2))


def fetchall(cur) -> list:
    return cur.fetchall()


# --------------------------------------------------------------- load
def load():
    fact = pd.read_csv(DATA / "fact_interaction.csv", parse_dates=["start_ts", "end_ts"])
    ch = pd.read_csv(DATA / "dim_channel.csv")
    q = pd.read_csv(DATA / "dim_queue.csv")
    ag = pd.read_csv(DATA / "dim_agent.csv")
    df = (fact
          .merge(ch[["channel_id", "channel", "channel_zh", "is_synchronous", "sla_target_seconds"]],
                 on="channel_id", how="left")
          .merge(q[["queue_id", "queue", "queue_zh"]], on="queue_id", how="left")
          .merge(ag[["agent_id", "team", "site"]], on="agent_id", how="left"))
    return fact, df


# --------------------------------------------------------------- KPIs
def headline(df: pd.DataFrame) -> list[tuple[str, str]]:
    answered = df[df["is_answered"]]
    sync = answered[answered["is_synchronous"]]
    async_ = answered[~answered["is_synchronous"]]
    cases = df.drop_duplicates("case_id")
    closed_cases = df[df["contact_seq"] == df["case_contact_count"]]
    resp = df[df["responded"]]

    sla = answered["is_within_sla"].mean()
    fcr = cases["is_first_contact_resolved"].mean()
    rep = (df["contact_seq"] > 1).mean()
    esc = cases["is_escalated"].mean()
    topbox = (resp["csat_score"] >= 4).mean()
    promoters = (resp["nps_score"] >= 9).mean()
    detractors = (resp["nps_score"] <= 6).mean()
    nps = (promoters - detractors) * 100   # NPS is reported in points, not as a fraction
    ces_easy = (resp["ces_score"] >= 5).mean()
    open_c = df[df["is_open"]]
    response_rate = len(resp) / len(closed_cases)

    rows = [
        ("Contacts", f"{len(df):,}"),
        ("Cases", f"{df['case_id'].nunique():,}"),
        ("Contacts per case", f"{len(df) / df['case_id'].nunique():.2f}"),
        ("Answered contacts", f"{len(answered):,}"),
        ("Abandonment rate", f"{df['is_abandoned'].mean():.1%}"),
        ("SLA attainment (answered)", f"{sla:.1%}"),
        ("ASA - avg queue wait, real-time channels", f"{sync['wait_seconds'].mean():.0f} s"),
        ("Avg first response, async channels", f"{async_['wait_seconds'].mean() / 3600:.1f} h"),
        ("AHT - avg handle time", f"{answered['handle_seconds'].mean():.0f} s ({answered['handle_seconds'].mean() / 60:.1f} min)"),
        ("FCR (case level, resolved first contact)", f"{fcr:.1%}"),
        ("Repeat contact rate (contacts that are follow-ups)", f"{rep:.1%}"),
        ("Escalation rate (case level)", f"{esc:.1%}"),
        ("Survey response rate (closed cases)", f"{response_rate:.1%}"),
        ("CSAT top-box (4-5 of 5)", f"{topbox:.1%}"),
        ("CSAT mean", f"{resp['csat_score'].mean():.2f} / 5"),
        ("CES mean", f"{resp['ces_score'].mean():.2f} / 7"),
        ("CES % easy (5-7 of 7)", f"{ces_easy:.1%}"),
        ("NPS", f"{nps:+.1f}  (promoters {promoters:.1%}, detractors {detractors:.1%})"),
        ("Cost per contact", f"MOP {df['cost_mop'].mean():.2f}"),
        ("Total contact cost (6 months)", f"MOP {df['cost_mop'].sum():,.0f}"),
        ("Open backlog now", f"{len(open_c):,} contacts"),
        ("Oldest open contact", f"{open_c['age_days'].max():.0f} days"),
    ]
    return rows


def by_group(df: pd.DataFrame, key: str) -> pd.DataFrame:
    answered = df[df["is_answered"]]
    resp = df[df["responded"]]
    g = df.groupby(key)
    out = pd.DataFrame({
        "contacts": g.size(),
        "sla_pct": answered.groupby(key)["is_within_sla"].mean(),
        "asa_sec": answered.groupby(key)["wait_seconds"].mean(),
        "aht_sec": answered.groupby(key)["handle_seconds"].mean(),
        "fcr_pct": df.drop_duplicates("case_id").groupby(key)["is_first_contact_resolved"].mean(),
        "csat": resp.groupby(key)["csat_score"].mean(),
        "ces": resp.groupby(key)["ces_score"].mean(),
    })
    nps = resp.assign(p=np.where(resp["nps_score"] >= 9, 1, np.where(resp["nps_score"] <= 6, -1, 0)))
    out["nps"] = nps.groupby(key)["p"].mean() * 100
    out["cost_per_contact"] = g["cost_mop"].mean()
    return out.round(2).sort_values("contacts", ascending=False)


def weekly(df: pd.DataFrame) -> pd.DataFrame:
    resp = df[df["responded"]]
    answered = df[df["is_answered"]]
    sync = answered[answered["is_synchronous"]]
    async_ = answered[~answered["is_synchronous"]]
    case = df.drop_duplicates("case_id")
    w = pd.DataFrame({
        "contacts": df.groupby("week_index").size(),
        "sla_pct": answered.groupby("week_index")["is_within_sla"].mean(),
        "asa_sec_sync": sync.groupby("week_index")["wait_seconds"].mean(),
        "frt_hours_async": async_.groupby("week_index")["wait_seconds"].mean() / 3600,
        "aht_sec": answered.groupby("week_index")["handle_seconds"].mean(),
        "open_backlog": df.groupby("week_index")["is_open"].sum(),
    })
    w["csat"] = resp.groupby("week_index")["csat_score"].mean()
    w["ces"] = resp.groupby("week_index")["ces_score"].mean()
    nps = resp.assign(p=np.where(resp["nps_score"] >= 9, 1, np.where(resp["nps_score"] <= 6, -1, 0)))
    w["nps"] = nps.groupby("week_index")["p"].mean() * 100
    w["fcr_pct"] = case.groupby("week_index")["is_first_contact_resolved"].mean()
    return w.round(3)


# --------------------------------------------------------------- effect checks
def checks(df: pd.DataFrame) -> list[str]:
    out = []
    case = df.drop_duplicates("case_id")
    phone = df[(df["channel"] == "Phone") & df["responded"]]
    early = phone[phone["week_index"] <= 13]
    late = phone[phone["week_index"] >= 14]

    d, ci, p = welch(late["ces_score"].to_numpy(), early["ces_score"].to_numpy())
    dw, ciw, _ = welch(late["wait_seconds"].to_numpy(), early["wait_seconds"].to_numpy())
    dc, cic, pc = welch(late["csat_score"].to_numpy(), early["csat_score"].to_numpy())
    out.append(
        "**1. Phone staffing gap (from week 14).** Phone wait {:.0f}s -> {:.0f}s "
        "(+{:.0f}s). CES {:.2f} -> {:.2f} (diff {:+.2f}, 95% CI +/-{:.2f}, p={:.1e}); "
        "CSAT {:.2f} -> {:.2f} (diff {:+.2f}, p={:.1e})."
        .format(early["wait_seconds"].mean(), late["wait_seconds"].mean(), dw,
                early["ces_score"].mean(), late["ces_score"].mean(), d, ci, p,
                early["csat_score"].mean(), late["csat_score"].mean(), dc, pc))

    em = df[df["channel"] == "Email"]
    e_before = em[em["week_index"] <= 22]
    e_after = em[em["week_index"] >= 23]
    k1, n1 = int(e_before["is_within_sla"].sum()), int(e_before["is_answered"].sum())
    k2, n2 = int(e_after["is_within_sla"].sum()), int(e_after["is_answered"].sum())
    diff, pz = two_prop_z(k2, n2, k1, n1)
    out.append(
        "**2. Email backlog (from week 23).** Email first-response SLA {:.1%} -> {:.1%} "
        "(diff {:+.1%}, p={:.1e}); email contacts still open {:,} of {:,} after week 23 vs "
        "{:,} of {:,} before; oldest open email contact {:.0f} days."
        .format(k1 / n1, k2 / n2, diff, pz,
                int(e_after["is_open"].sum()), len(e_after),
                int(e_before["is_open"].sum()), len(e_before),
                em[em["is_open"]]["age_days"].max()))

    f = case.groupby("channel")["is_first_contact_resolved"].mean()
    out.append(
        "**3. Channel resolution gap.** FCR by channel: "
        + ", ".join(f"{k} {v:.1%}" for k, v in f.sort_values(ascending=False).items())
        + ".")

    weeks = case.assign(week=case["week_index"])
    billing = case[case["queue"] == "Billing"]
    spike = billing[billing["week_index"].isin([18, 19])]["week_index"].value_counts().sum()
    base = billing[~billing["week_index"].isin([18, 19])]["week_index"].value_counts().mean()
    resp_b = df[(df["queue"] == "Billing") & df["responded"]]
    cs_peak = resp_b[resp_b["week_index"].isin([18, 19])]["csat_score"].mean()
    cs_base = resp_b[~resp_b["week_index"].isin([18, 19])]["csat_score"].mean()
    out.append(
        "**4. Billing volume spike without an experience change.** Billing cases/week "
        "{:.0f} -> {:.0f} during weeks 18-19, while Billing CSAT stayed {:.2f} vs {:.2f} "
        "(diff {:+.2f}). Volume is not the same signal as experience."
        .format(base, spike / 2, cs_peak, cs_base, cs_peak - cs_base))

    rq = df[df["responded"]].groupby("queue").agg(csat=("csat_score", "mean"))
    nps_q = (df[df["responded"]]
             .assign(p=lambda d: np.where(d["nps_score"] >= 9, 1, np.where(d["nps_score"] <= 6, -1, 0)))
             .groupby("queue")["p"].mean() * 100)
    out.append(
        "**5. Worst queue by satisfaction.** "
        + ", ".join(f"{q} CSAT {rq.loc[q, 'csat']:.2f} / NPS {nps_q[q]:+.0f}"
                    for q in rq["csat"].sort_values().index)
        + ".")

    r = df[df["responded"]].dropna(subset=["csat_score"])
    sync_r = r[r["is_synchronous"]]
    corr_sync = np.corrcoef(np.log1p(sync_r["wait_seconds"]), sync_r["csat_score"])[0, 1]
    lw = np.log1p(r["wait_seconds"])
    z = lw.groupby(r["channel"]).transform(lambda s: (s - s.mean()) / (s.std() + 1e-9))
    corr_z = np.corrcoef(z, r["csat_score"])[0, 1]
    ces_wait_sync = np.corrcoef(np.log1p(sync_r["wait_seconds"]), sync_r["ces_score"])[0, 1]
    esc = r.groupby("is_escalated")["csat_score"].mean()
    out.append(
        "**Supporting drivers.** corr(log wait, CSAT) = {:.2f} and corr(log wait, CES) = {:.2f} "
        "for real-time channels (queue wait is only comparable there); corr(wait z-score within "
        "channel, CSAT) = {:.2f}. CSAT {:.2f} when escalated vs {:.2f} when not "
        "({:.2f} lower); CSAT {:.2f} when resolved first contact vs {:.2f} when not."
        .format(corr_sync, ces_wait_sync, corr_z, esc[True], esc[False], esc[False] - esc[True],
                r[r["case_contact_count"] == 1]["csat_score"].mean(),
                r[r["case_contact_count"] > 1]["csat_score"].mean()))
    return out


# --------------------------------------------------------------- charts
def charts(df: pd.DataFrame, kw: pd.DataFrame) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"figure.dpi": 130, "axes.spines.top": False, "axes.spines.right": False,
                         "axes.grid": True, "grid.alpha": 0.25, "font.size": 9})

    fig, ax1 = plt.subplots(figsize=(9, 4))
    ax1.bar(kw.index, kw["contacts"], color="#c9d6e8", label="Contacts")
    ax1.set_ylabel("Contacts")
    ax1.set_xlabel("Reporting week")
    ax2 = ax1.twinx()
    ax2.plot(kw.index, kw["sla_pct"] * 100, color="#1b5e9c", marker="o", ms=3,
             label="SLA attainment %")
    ax2.set_ylabel("SLA attainment %")
    ax2.grid(False)
    ax1.axvspan(13.5, 26.5, color="#f2c14e", alpha=0.12)
    ax1.set_title("Contacts vs SLA attainment — phone staffing gap from week 14 (shaded)")
    fig.tight_layout()
    fig.savefig(OUT / "01_volume_vs_sla.png")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 4))
    ax.plot(kw.index, kw["csat"], marker="o", ms=3, label="CSAT (1-5)")
    ax.plot(kw.index, kw["ces"], marker="s", ms=3, label="CES (1-7)")
    ax.plot(kw.index, kw["nps"] / 50 + 3, marker="^", ms=3, ls="--",
            label="NPS (points, rescaled /50 +3)")
    ax.axvline(13.5, color="#c0392b", lw=1)
    ax.axvline(22.5, color="#7d3c98", lw=1)
    ax.set_xlabel("Reporting week")
    ax.set_ylabel("Score")
    ax.set_title("Satisfaction trend — phone gap at week 14, email backlog at week 23")
    ax.legend(loc="lower left")
    fig.tight_layout()
    fig.savefig(OUT / "02_satisfaction_trend.png")
    plt.close(fig)

    op = df[df["is_open"]].copy()
    buckets = pd.cut(op["age_days"], [0, 1, 3, 7, 14, 30, 10_000],
                     labels=["0-1d", "1-3d", "3-7d", "7-14d", "14-30d", "30d+"])
    mixed = op.assign(b=buckets).groupby(["b", "channel"], observed=True).size().unstack(fill_value=0)
    fig, ax = plt.subplots(figsize=(9, 4))
    mixed.plot(kind="bar", stacked=True, ax=ax, colormap="tab20c")
    ax.set_xlabel("Backlog age bucket")
    ax.set_ylabel("Open contacts")
    ax.set_title("Open backlog by age and channel — aging concentrates in Email")
    ax.legend(title="Channel", fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "03_backlog_aging.png")
    plt.close(fig)

    rq = df[df["responded"]].groupby("queue").agg(csat=("csat_score", "mean"), ces=("ces_score", "mean"))
    nps_q = (df[df["responded"]]
             .assign(p=lambda d: np.where(d["nps_score"] >= 9, 1, np.where(d["nps_score"] <= 6, -1, 0)))
             .groupby("queue")["p"].mean() * 100)
    rq = rq.join(nps_q.rename("nps")).sort_values("csat")
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.barh(rq.index, rq["csat"], color="#1b5e9c")
    for i, (cs, np_) in enumerate(zip(rq["csat"], rq["nps"])):
        ax.text(cs + 0.02, i, f"{cs:.2f}  (NPS {np_:+.0f})", va="center", fontsize=8)
    ax.set_xlim(0, 5.4)
    ax.set_xlabel("CSAT (1-5)")
    ax.set_title("CSAT and NPS by service queue")
    fig.tight_layout()
    fig.savefig(OUT / "04_queue_satisfaction.png")
    plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fact, df = load()

    kw = weekly(df)
    kw.to_csv(OUT / "kpi_weekly.csv", encoding="utf-8-sig")
    by_group(df, "queue").to_csv(OUT / "kpi_by_queue.csv", encoding="utf-8-sig")
    by_group(df, "channel").to_csv(OUT / "kpi_by_channel.csv", encoding="utf-8-sig")

    head = headline(df)
    eff = checks(df)
    lines = ["# KPI reference (pandas) — synthetic 26-week customer service dataset",
             "",
             f"Snapshot as-of: {AS_OF.date()}. Source: `data/*.csv` (generated by `src/generate_data.py`).",
             "Every number below is what the Power BI dashboard must reproduce.",
             "",
             "## Headline KPIs", ""]
    lines += [f"| {k} | {v} |" for k, v in head]
    lines += ["", "## Findings (verified in this run)", ""] + [f"- {e}" for e in eff]
    lines += ["", "## Weekly trend (first and last 3 weeks)", "",
              "```", kw.head(3).to_string(), "...", kw.tail(3).to_string(), "```", "",
              "## By queue", "", "```", by_group(df, "queue").to_string(), "```", "",
              "## By channel", "", "```", by_group(df, "channel").to_string(), "```", ""]
    (OUT / "kpi_reference.md").write_text("\n".join(lines), encoding="utf-8")

    charts(df, kw)

    print("contacts:", len(df), "cases:", fact["case_id"].nunique())
    for e in eff:
        print("*", e[:150])
    print("wrote outputs/kpi_reference.md, kpi_weekly.csv, kpi_by_queue.csv, kpi_by_channel.csv, 4 PNGs")


if __name__ == "__main__":
    main()
