"""Synthetic customer-service operations dataset for the CX ops dashboard.

Grain
-----
fact_interaction: one row per CONTACT (call / email / chat / social message / web form).
A CASE is one customer issue; a case needing follow-up produces 2-3 contacts
(contact_seq 1..n), which is how repeat-contact and FCR are measured honestly.

All data is SYNTHETIC (seeded, reproducible). No real customer data is used.

Planted effects (deliberate, so the dashboard has something real to find)
-----------------------------------------------------------------------
1. Phone staffing gap from week 14 -> phone wait x2.1 -> CES and CSAT fall.
2. Email backlog from week 23  -> first-response SLA breaches + aging buckets fill
   because open contacts never close.
3. Live Chat resolves more cases first-contact (FCR .78) than Phone (.61).
4. Billing volume spikes in weeks 18-19 (campaign) with NO satisfaction change
   -> volume is not the same thing as an experience problem.
5. Complaints & Escalations has the lowest CSAT/NPS of all queues.

Run:  python src/generate_data.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

SEED = 20261005
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

END = pd.Timestamp("2026-10-04")            # last full day (Sunday)
START = END - pd.Timedelta(days=181)        # 182 days = 26 whole weeks
AS_OF = END + pd.Timedelta(days=1)          # reporting snapshot for backlog aging
DATES = pd.date_range(START, END, freq="D")
N_WEEKS = 26

# ---------------------------------------------------------------- dimensions

CHANNELS = [
    # name,        p,     sync, unit_cost_mop, sla_target_s, base_talk_s, fcr, sat_off, resp_p
    ("Phone",      0.42,  True,  22.0,          60,           320,        0.64, -0.10, 0.30),
    ("Email",      0.26,  False,  9.0,          14400,        240,        0.72,  0.05, 0.24),
    ("Live Chat",  0.19,  True,   7.0,          45,           260,        0.78,  0.20, 0.34),
    ("Social Media", 0.06, False, 6.0,          28800,        180,        0.66, -0.05, 0.18),
    ("Web Form",   0.07,  False,  2.0,          43200,        150,        0.69,  0.10, 0.10),
]
CHANNEL_ZH = {
    "Phone": "電話", "Email": "電郵", "Live Chat": "線上對話",
    "Social Media": "社交媒體", "Web Form": "網上表格",
}

QUEUES = ["Billing", "Technical Support", "Delivery & Logistics",
          "Account Management", "Complaints & Escalations"]
QUEUE_ZH = {
    "Billing": "帳務", "Technical Support": "技術支援",
    "Delivery & Logistics": "配送與物流", "Account Management": "客戶帳戶管理",
    "Complaints & Escalations": "投訴與升級",
}
QUEUE_SAT_OFFSET = {"Billing": 0.0, "Technical Support": -0.10,
                    "Delivery & Logistics": -0.25, "Account Management": 0.05,
                    "Complaints & Escalations": -0.65}

# channel x queue mix (rows sum to 1)
QUEUE_MIX = np.array([
    [0.30, 0.30, 0.10, 0.15, 0.15],   # Phone
    [0.25, 0.25, 0.20, 0.22, 0.08],   # Email
    [0.22, 0.35, 0.12, 0.25, 0.06],   # Live Chat
    [0.18, 0.20, 0.15, 0.32, 0.15],   # Social Media
    [0.24, 0.22, 0.26, 0.24, 0.04],   # Web Form
])

STATUSES = [
    ("Resolved", "已解決", False, False),
    ("Closed", "已結案", False, False),
    ("Open", "待處理", True, False),
    ("Pending", "待覆", True, False),
    ("Abandoned", "放棄", False, True),
]

WEEKDAY_FACTOR = {"Monday": 1.22, "Tuesday": 1.12, "Wednesday": 1.05,
                  "Thursday": 1.02, "Friday": 1.00, "Saturday": 0.62, "Sunday": 0.42}


def build_dims(rng: np.random.Generator):
    dim_date = pd.DataFrame({"date": DATES})
    dim_date["date_key"] = dim_date["date"].dt.strftime("%Y%m%d").astype(int)
    dim_date["year"] = dim_date["date"].dt.year
    dim_date["quarter"] = dim_date["date"].dt.quarter
    dim_date["month"] = dim_date["date"].dt.month
    dim_date["month_name"] = dim_date["date"].dt.strftime("%B")
    dim_date["week_index"] = (dim_date["date"] - START).dt.days // 7 + 1
    dim_date["week_start_date"] = START + pd.to_timedelta((dim_date["week_index"] - 1) * 7, unit="D")
    dim_date["weekday_name"] = dim_date["date"].dt.day_name()
    dim_date["weekday_num"] = dim_date["date"].dt.dayofweek + 1
    dim_date["is_weekend"] = dim_date["weekday_num"] >= 6

    dim_channel = pd.DataFrame(
        [(i + 1, c[0], CHANNEL_ZH[c[0]], c[2], c[3], c[4]) for i, c in enumerate(CHANNELS)],
        columns=["channel_id", "channel", "channel_zh", "is_synchronous",
                 "unit_cost_mop", "sla_target_seconds"],
    )
    dim_queue = pd.DataFrame(
        [(i + 1, q, QUEUE_ZH[q], QUEUE_SAT_OFFSET[q]) for i, q in enumerate(QUEUES)],
        columns=["queue_id", "queue", "queue_zh", "satisfaction_offset"],
    )
    dim_status = pd.DataFrame(STATUSES,
                              columns=["status", "status_zh", "is_open", "is_abandoned"])

    teams = ["Inbound Phone", "Email Desk", "Chat Desk", "Escalations"]
    sites = ["Macau HQ", "Taipa Annex", "Remote"]
    n_agents = 42
    dim_agent = pd.DataFrame({
        "agent_id": np.arange(1, n_agents + 1),
        "agent_code": [f"AG{i:03d}" for i in range(1, n_agents + 1)],
        "team": rng.choice(teams, n_agents, p=[0.45, 0.25, 0.20, 0.10]),
        "site": rng.choice(sites, n_agents, p=[0.55, 0.30, 0.15]),
        "tenure_months": rng.integers(1, 97, n_agents),
    })

    n_customers = 6500
    dim_customer = pd.DataFrame({
        "customer_id": np.arange(1, n_customers + 1),
        "segment": rng.choice(["Consumer", "Business"], n_customers, p=[0.82, 0.18]),
        "region": rng.choice(["Macau Peninsula", "Taipa", "Coloane", "Other"],
                             n_customers, p=[0.55, 0.28, 0.07, 0.10]),
        "tenure_months": rng.integers(1, 121, n_customers),
        "is_new_customer": rng.random(n_customers) < 0.22,
    })
    return dim_date, dim_channel, dim_queue, dim_status, dim_agent, dim_customer


def daily_case_weights() -> np.ndarray:
    """Expected cases per day: weekday seasonality + slow growth + campaign spike."""
    w = np.empty(len(DATES))
    for i, d in enumerate(DATES):
        week = i // 7 + 1
        base = 108.0 * (1 + 0.0025 * i) * WEEKDAY_FACTOR[d.day_name()]
        if week in (18, 19):                      # effect 4: campaign, Billing-heavy
            base *= 1.18
        w[i] = base
    return w


def generate(seed: int = SEED):
    rng = np.random.default_rng(seed)
    dim_date, dim_channel, dim_queue, dim_status, dim_agent, dim_customer = build_dims(rng)

    ch_names = [c[0] for c in CHANNELS]
    ch_p = np.array([c[1] for c in CHANNELS])
    ch_p = ch_p / ch_p.sum()
    ch_cost = np.array([c[3] for c in CHANNELS])
    ch_sla = np.array([c[4] for c in CHANNELS])
    ch_fcr = np.array([c[6] for c in CHANNELS])
    ch_sat = np.array([c[7] for c in CHANNELS])
    ch_resp = np.array([c[8] for c in CHANNELS])

    # ---- case-level volume -------------------------------------------------
    weights = daily_case_weights()
    p_day = weights / weights.sum()
    n_cases = int(rng.poisson(weights.sum() * 0.70))   # some days carry >1 case per draw item
    day_idx = rng.choice(len(DATES), size=n_cases, p=p_day)

    channel_idx = rng.choice(len(CHANNELS), size=n_cases, p=ch_p)
    queue_idx = np.array([rng.choice(len(QUEUES), p=QUEUE_MIX[c]) for c in channel_idx])
    if rng.random() < 1.0:                              # campaign skews Billing (effect 4)
        weeks = day_idx // 7 + 1
        bump = (weeks >= 18) & (weeks <= 19)
        to_billing = bump & (rng.random(n_cases) < 0.18)
        queue_idx[to_billing] = 0

    hour = rng.integers(8, 21, n_cases)
    start_ts = pd.to_datetime(DATES[day_idx]) + pd.to_timedelta(hour, unit="h") \
        + pd.to_timedelta(rng.integers(0, 60, n_cases), unit="m") \
        + pd.to_timedelta(rng.integers(0, 60, n_cases), unit="s")
    week = np.asarray((start_ts - START).days // 7 + 1)

    # ---- wait seconds (queue wait for sync, first-response for async) ------
    phone_gap = (channel_idx == 0) & (week >= 14)       # effect 1
    email_backlog = (channel_idx == 1) & (week >= 23)   # effect 2
    wait_median = np.select(
        [channel_idx == 0, channel_idx == 1, channel_idx == 2, channel_idx == 3, channel_idx == 4],
        [42.0, 9000.0, 55.0, 14000.0, 20000.0],
    )
    wait_median = wait_median * np.where(phone_gap, 2.1, 1.0) * np.where(email_backlog, 2.5, 1.0)
    wait_seconds = np.round(wait_median * rng.lognormal(mean=0.0, sigma=0.55, size=n_cases)).astype(int)

    sync = np.array([CHANNELS[c][2] for c in channel_idx])
    p_abandon = np.clip(0.02 + wait_seconds / 900.0, 0, 0.22) * sync
    is_abandoned = rng.random(n_cases) < p_abandon
    is_answered = ~is_abandoned

    # ---- resolution / repeat contacts --------------------------------------
    escalated = rng.random(n_cases) < np.where(queue_idx == 4, 0.34, 0.09)
    p_fcr = ch_fcr[channel_idx] - np.where(escalated, 0.12, 0.0) - np.where(phone_gap, 0.06, 0.0)
    fcr = rng.random(n_cases) < np.clip(p_fcr, 0.05, 0.95)
    fcr = fcr & is_answered

    extra = np.where(fcr, 0, rng.integers(1, 3, n_cases))
    n_contacts = np.where(is_answered, 1 + extra, 1)
    # a series cannot run past the reporting window: one contact per available day max
    days_avail = np.asarray((END - start_ts).days) + 1
    n_contacts = np.minimum(n_contacts, np.maximum(days_avail, 1))

    base_talk = np.array([CHANNELS[c][5] for c in channel_idx])
    talk = np.round(base_talk * rng.lognormal(0.0, 0.32, n_cases)).astype(int)
    wrap = np.round(talk * rng.uniform(0.10, 0.30, n_cases)).astype(int)
    transfers = rng.choice([0, 1, 2], n_cases, p=[0.72, 0.21, 0.07]) + np.where(escalated, 1, 0)

    # latent satisfaction drives CSAT / CES / NPS together
    lw = np.log1p(wait_seconds)
    z_wait = np.zeros_like(lw)
    for c in range(len(CHANNELS)):                 # standardise wait within each channel
        m = channel_idx == c
        z_wait[m] = (lw[m] - lw[m].mean()) / (lw[m].std() + 1e-9)
    latent = (4.75 + ch_sat[channel_idx]
              + np.array([QUEUE_SAT_OFFSET[q] for q in QUEUES])[queue_idx]
              - 0.45 * np.clip(z_wait, -2, 3)
              - 0.50 * (transfers >= 2)
              - 0.70 * escalated
              - 0.95 * (~fcr)
              - np.where(phone_gap, 0.30, 0.0)          # effect 1 (experience, not just wait)
              + rng.normal(0, 0.55, n_cases))

    responded = rng.random(n_cases) < ch_resp[channel_idx]
    csat = np.clip(np.round(latent + rng.normal(0, 0.25, n_cases)), 1, 5)
    ces = np.clip(np.round(1.0 + (latent - 1.0) * 1.25 + rng.normal(0, 0.5, n_cases)), 1, 7)
    nps = np.clip(np.round(2.2 * (latent - 0.5) + rng.normal(0, 1.3, n_cases)), 0, 10)

    # ---- expand cases -> contacts ------------------------------------------
    frames = []
    case_ids = np.arange(1, n_cases + 1)
    cum = np.zeros(n_cases, dtype=int)
    for slot in range(int(n_contacts.max())):
        keep = n_contacts > slot
        if not keep.any():
            continue
        gap_days = np.zeros(int(keep.sum()), dtype=int)
        if slot > 0:
            gap = rng.integers(1, 8, n_cases)
            cum = cum + np.minimum(gap, np.maximum(days_avail - cum, 1))
            cum = np.minimum(cum, days_avail)
            gap_days = cum[keep]
        contact_ts = (start_ts.to_numpy()[keep] + pd.to_timedelta(gap_days, unit="D")
                      + pd.to_timedelta(slot * 137, unit="s"))
        recent = contact_ts >= np.datetime64(END - pd.Timedelta(days=45))
        closing = (slot == n_contacts[keep] - 1)
        status = np.where(closing, "Resolved", "Closed")
        pending = closing & recent & ~is_abandoned[keep] & (rng.random(int(keep.sum())) < 0.05)
        status = np.where(pending, "Pending", status)
        open_case = pending
        status = np.where(is_abandoned[keep], "Abandoned", status)

        df = pd.DataFrame({
            "case_id": case_ids[keep],
            "customer_id": rng.choice(dim_customer["customer_id"], keep.sum()),
            "agent_id": rng.choice(dim_agent["agent_id"], keep.sum()),
            "channel_id": channel_idx[keep] + 1,
            "queue_id": queue_idx[keep] + 1,
            "start_ts": contact_ts,
            "contact_seq": slot + 1,
            "case_contact_count": n_contacts[keep],
            "is_first_contact_resolved": (slot == 0) & fcr[keep],
            "is_repeat_contact": slot > 0,
            "is_answered": is_answered[keep],
            "is_abandoned": is_abandoned[keep],
            "wait_seconds": wait_seconds[keep],
            "talk_seconds": np.where(is_answered[keep], talk[keep], 0),
            "wrap_seconds": np.where(is_answered[keep], wrap[keep], 0),
            "transfer_count": transfers[keep],
            "is_escalated": escalated[keep],
            "status": status,
            "is_open": open_case,
            "sla_target_seconds": ch_sla[channel_idx[keep]],
            "unit_cost_mop": ch_cost[channel_idx[keep]],
            "responded": responded[keep] & closing,
            "csat_score": csat[keep],
            "ces_score": ces[keep],
            "nps_score": nps[keep],
            "latent_satisfaction": latent[keep],
        })
        frames.append(df)

    fact = pd.concat(frames, ignore_index=True)
    fact = fact.sort_values(["case_id", "contact_seq"]).reset_index(drop=True)

    # ---- effect 2: email backlog keeps some contacts open ------------------
    email_recent = (fact["channel_id"] == 2) & (fact["contact_seq"] == fact["case_contact_count"]) \
        & (fact["start_ts"] >= END - pd.Timedelta(days=28)) & fact["is_answered"]
    fact.loc[email_recent & (rng.random(len(fact)) < 0.30), "is_open"] = True
    fact.loc[fact["is_open"], "status"] = np.where(
        fact.loc[fact["is_open"], "status"] == "Resolved", "Open", fact.loc[fact["is_open"], "status"])

    fact["handle_seconds"] = fact["talk_seconds"] + fact["wrap_seconds"]
    closed_end = fact["start_ts"] + pd.to_timedelta(
        fact["wait_seconds"] + fact["handle_seconds"], unit="s")
    fact["end_ts"] = closed_end.where(~fact["is_open"])
    fact["is_within_sla"] = fact["is_answered"] & (fact["wait_seconds"] <= fact["sla_target_seconds"])
    age_open = ((AS_OF - fact["start_ts"]).dt.total_seconds() / 86400.0).to_numpy()
    age_closed = ((fact["end_ts"] - fact["start_ts"]).dt.total_seconds() / 86400.0).to_numpy()
    fact["age_days"] = np.where(fact["is_open"].to_numpy(), age_open, age_closed).round(2)
    fact["cost_mop"] = np.where(fact["is_answered"], fact["unit_cost_mop"], fact["unit_cost_mop"] * 0.35).round(2)

    # surveys only exist for a single contact per case (the closing one)
    closing = fact["contact_seq"] == fact["case_contact_count"]
    for c in ("csat_score", "ces_score", "nps_score"):
        fact[c] = fact[c].where(closing & fact["responded"])
    fact["responded"] = fact["responded"] & closing

    fact["date_key"] = fact["start_ts"].dt.strftime("%Y%m%d").astype(int)
    fact["week_index"] = (fact["start_ts"] - START).dt.days // 7 + 1
    fact["hour_of_day"] = fact["start_ts"].dt.hour
    fact["interaction_id"] = ["I" + str(i).zfill(7) for i in range(1, len(fact) + 1)]

    cols = ["interaction_id", "case_id", "customer_id", "agent_id", "channel_id", "queue_id",
            "date_key", "start_ts", "end_ts", "week_index", "hour_of_day",
            "contact_seq", "case_contact_count", "is_first_contact_resolved", "is_repeat_contact",
            "is_answered", "is_abandoned", "is_open", "status",
            "wait_seconds", "talk_seconds", "wrap_seconds", "handle_seconds",
            "transfer_count", "is_escalated", "sla_target_seconds", "is_within_sla",
            "age_days", "cost_mop", "responded", "csat_score", "ces_score", "nps_score"]
    return fact[cols], dim_date, dim_channel, dim_queue, dim_status, dim_agent, dim_customer


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    fact, *dims = generate()
    fact.to_csv(DATA / "fact_interaction.csv", index=False, encoding="utf-8-sig",
                date_format="%Y-%m-%d %H:%M:%S")
    for d, name in zip(dims, ["dim_date", "dim_channel", "dim_queue", "dim_status",
                              "dim_agent", "dim_customer"]):
        d.to_csv(DATA / f"{name}.csv", index=False, encoding="utf-8-sig",
                 date_format="%Y-%m-%d")

    print("fact_interaction.csv rows:", len(fact))
    print("cases:", fact["case_id"].nunique())
    print("date range:", fact["start_ts"].min(), "->", fact["start_ts"].max())
    print("open contacts:", int(fact["is_open"].sum()))
    print("abandoned:", int(fact["is_abandoned"].sum()))
    print("survey responses:", int(fact["responded"].sum()))
    print("fcr %:", round(100 * fact.loc[fact["contact_seq"] == 1, "is_first_contact_resolved"].mean(), 1))


if __name__ == "__main__":
    main()
