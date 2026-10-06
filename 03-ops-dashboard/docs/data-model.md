# Data model — star schema for the service operations dashboard

```
                     ┌────────────────┐
                     │   dim_date     │  marked as date table (dim_date[date])
                     │ date_key (PK)  │
                     └───────┬────────┘
                             │
┌────────────────┐   ┌───────┴─────────┐   ┌────────────────┐
│  dim_channel   ├───┤ fact_interaction├───┤   dim_queue    │
│ channel_id(PK) │   │  23,162 rows    │   │  queue_id (PK) │
└────────────────┘   │  grain: contact │   └────────────────┘
                     │                 │
┌────────────────┐   │                 │   ┌────────────────┐
│   dim_agent    ├───┤                 ├───┤ dim_customer   │
│  agent_id (PK) │   │                 │   │customer_id (PK)│
└────────────────┘   └───────┬─────────┘   └────────────────┘
                             │
                     ┌───────┴────────┐
                     │  dim_status    │  status is the join key (text)
                     │ status (PK)    │
                     └────────────────┘
```

## Relationships (all many-to-one, single direction)

| From (fact) | To (dimension) | Cardinality |
|---|---|---|
| `fact_interaction[date_key]` | `dim_date[date_key]` | * → 1 |
| `fact_interaction[channel_id]` | `dim_channel[channel_id]` | * → 1 |
| `fact_interaction[queue_id]` | `dim_queue[queue_id]` | * → 1 |
| `fact_interaction[agent_id]` | `dim_agent[agent_id]` | * → 1 |
| `fact_interaction[customer_id]` | `dim_customer[customer_id]` | * → 1 |
| `fact_interaction[status]` | `dim_status[status]` | * → 1 |

## fact_interaction columns

| Column | Type | Meaning |
|---|---|---|
| `interaction_id` | text | Contact business key (unique) |
| `case_id` | int | Issue key; 1..n contacts share it — the basis for FCR and repeat contacts |
| `customer_id`, `agent_id`, `channel_id`, `queue_id` | int | Dimension keys |
| `date_key` | int (yyyymmdd) | Join to `dim_date` |
| `start_ts`, `end_ts` | datetime | `end_ts` is null while a contact is open |
| `week_index`, `hour_of_day` | int | Convenience slicers |
| `contact_seq`, `case_contact_count` | int | Position in the series; equality identifies the **closing contact** |
| `is_first_contact_resolved` | bool | TRUE only on contact 1 of a case that closed on that contact |
| `is_repeat_contact` | bool | `contact_seq > 1` |
| `is_answered`, `is_abandoned`, `is_open` | bool | Contact state flags |
| `status` | text | Resolved / Closed / Open / Pending / Abandoned |
| `wait_seconds` | int | Queue wait (sync) or time to first response (async) |
| `talk_seconds`, `wrap_seconds`, `handle_seconds` | int | Handle = talk + wrap |
| `transfer_count`, `is_escalated` | int / bool | Friction (case-level flag repeated on each contact of the case) |
| `sla_target_seconds`, `is_within_sla` | int / bool | Target lives in `dim_channel`; the flag is materialised here for cheap aggregation |
| `age_days` | float | Snapshot age: closed = duration, open = age at snapshot |
| `cost_mop` | float | Fully-loaded cost per contact (MOP) |
| `responded`, `csat_score`, `ces_score`, `nps_score` | bool / int | Survey fields populated only on the closing contact of responded cases |

## Design decisions

**One fact table, not two.** A separate survey fact would create a second grain and force every
satisfaction visual to reconcile denominators. Instead the survey lives on the closing contact and every
satisfaction measure filters `responded = TRUE`. Fewer grains, fewer wrong numbers.

**Flags are materialised; rules live in one place.** `is_within_sla`, `is_first_contact_resolved` and
`is_escalated` are computed once (in the pipeline / generator) instead of being re-derived in twenty
DAX measures. When the definition changes, it changes in one file and every visual stays consistent.

**SLA target stays in `dim_channel` as the source of truth**, while the boolean outcome is stored on the
fact. A target is an attribute of a channel; an outcome is a property of a contact.

**Add one calculated column in Power BI** (used by response rate and by "closed contacts"):

```dax
is_closing_contact = fact_interaction[contact_seq] = fact_interaction[case_contact_count]
```

**Hide every key column** (`*_id`, `date_key`) from report view and sort `dim_queue[queue]` by a numeric
rank if you add one — an analyst-facing model should not require the business to know surrogate keys.

**Date table.** `dim_date` covers 2026-04-06 → 2026-10-04 with `year, quarter, month, month_name,
week_index, week_start_date, weekday_name, weekday_num, is_weekend`. Mark it as the date table
(Table tools → Mark as date table → `date`) so time-intelligence functions work.

## Row-level security (optional, for a real deployment)

```dax
// Role: Team Lead — Inbound Phone
[team] = "Inbound Phone"          // filter on dim_agent
```

```dax
// Role: Service Line Manager
[queue] = LOOKUPVALUE(dim_queue[queue], dim_queue[queue], [queue])
```

A manager role would filter `dim_queue`; agents would be restricted by `agent_id` to their own contacts.
Test with "View as role" before publishing.

## Data quality checks that should run before refresh

Implemented and executable in **`src/dq_checks.py`** (30 checks, exit code 1 on failure so it can gate a
pipeline refresh). Current run: **30/30 pass** on 23,162 rows / 15,721 cases.

| Check | Expected |
|---|---|
| `interaction_id` unique | 23,162 distinct |
| No orphan keys | every `channel_id`, `queue_id`, `agent_id`, `customer_id`, `date_key` exists in its dimension |
| Likert ranges | `csat_score ∈ 1..5`, `ces_score ∈ 1..7`, `nps_score ∈ 0..10`, nulls only when `responded = FALSE` |
| Survey placement | `responded = TRUE` implies `is_closing_contact` |
| SLA coherence | `is_within_sla = TRUE` implies `is_answered = TRUE` |
| Open contacts | `end_ts` is null and `age_days > 0` |
| Cost | `cost_mop` ≥ 0, no nulls |
| Date completeness | exactly 182 consecutive days, 26 complete weeks |
