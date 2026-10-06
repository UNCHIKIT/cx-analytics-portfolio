# Metric definitions — service operations dashboard

**Grain.** `fact_interaction` = one row per **contact** (a call, email, chat, social message or web form
submission). A **case** is one customer issue; a case that is not resolved first time produces 2–3
contacts (`contact_seq` 1..n) within 1–7 days. Every metric below states its grain explicitly,
because most CX reporting errors come from mixing contact-grain and case-grain numbers.

**Snapshot.** Data covers 2026-04-06 → 2026-10-04 (26 reporting weeks). Reference values are in
`outputs/kpi_reference.md`, produced by `src/kpi_reference.py` — the Power BI model must reproduce them.

**SLA targets differ by channel** because synchronous and asynchronous contacts are not comparable:

| Channel | 中文 | Type | SLA target | Meaning of the target |
|---|---|---|---|---|
| Phone | 電話 | sync | 60 s | answered within 60 s of entering the queue |
| Live Chat | 線上對話 | sync | 45 s | answered within 45 s |
| Email | 電郵 | async | 4 h | first response within 4 working hours |
| Social Media | 社交媒體 | async | 8 h | first response within 8 h |
| Web Form | 網上表格 | async | 12 h | first response within 12 h |

> Average queue wait (ASA) is only reported for **real-time channels**. Averaging a 49 s phone wait with
> a 4.3 h email first-response time produces a meaningless number — a classic dashboard mistake.

---

## Volume and demand

| Metric | 中文 | Formula | Notes |
|---|---|---|---|
| Contacts | 聯絡量 | `COUNTROWS(fact_interaction)` | Demand at contact grain |
| Cases | 個案量 | `DISTINCTCOUNT(case_id)` | True issue count |
| Contacts per case | 每案聯絡次數 | `Contacts / Cases` | Efficiency signal; >1.5 means repeat work |
| Abandonment rate | 放棄率 | `abandoned / contacts` | Only real-time channels can be abandoned |
| Contacts by channel / queue / week | — | slice | Demand mix, seasonality |

## Speed and service level

| Metric | 中文 | Formula | Notes |
|---|---|---|---|
| SLA attainment % | 服務水準達成率 | `contacts with is_within_sla / answered contacts` | Denominator is **answered** only; abandoned contacts cannot meet a target |
| ASA (s) | 平均等候時間 | `AVERAGE(wait_seconds)` filtered to sync channels | Queue wait |
| First response (h) | 平均首次回覆時間 | `AVERAGE(wait_seconds)/3600` filtered to async channels | Do not mix with ASA |
| AHT (s) | 平均處理時間 | `AVERAGE(talk_seconds + wrap_seconds)` on answered | Talk + after-call work, excludes queue wait |

## Resolution quality

| Metric | 中文 | Formula | Notes |
|---|---|---|---|
| FCR % | 首次聯絡解決率 | `distinct cases with is_first_contact_resolved / distinct cases` | **Case grain.** Never compute as contacts |
| Repeat contact rate | 重複聯絡率 | `contacts with contact_seq > 1 / contacts` | Contact grain; the mirror image of FCR |
| Escalation rate | 升級率 | `distinct cases with is_escalated / distinct cases` | Case grain |
| Transfer count | 轉接次數 | `AVERAGE(transfer_count)` | Friction indicator |

## Experience (survey, closing contact only)

A survey is sent on the **closing contact of a case**; only some customers respond. Everything below is
filtered to `responded = TRUE`, which is the denominator for every satisfaction metric.

| Metric | 中文 | Formula | Notes |
|---|---|---|---|
| CSAT top-box % | 滿意度（4–5 分比例） | `csat_score >= 4 / responded` | Top-box is the standard, not the mean |
| CSAT mean | 平均滿意度 | `AVERAGE(csat_score)` | 1–5 scale. Compare with top-box, never instead of it |
| CES mean | 平均努力度 | `AVERAGE(ces_score)` | 1–7, higher = easier |
| CES % easy | 容易比例 | `ces_score >= 5 / responded` | 5–7 band |
| NPS | 淨推薦值 | `(promoters 9–10 − detractors 0–6) / responded × 100` | Range −100…+100 |
| Survey response rate | 問卷回覆率 | `responded / closing contacts` | Below ~15% the results are not decision-grade |

> Mixed scales are not comparable: CSAT 4/5 = 80%, CES 4/7 = 57%, NPS +40 are three different things.
> Never average them into a "satisfaction index" without saying so.

## Cost

| Metric | 中文 | Formula |
|---|---|---|
| Cost per contact | 每次聯絡成本 | `SUM(cost_mop) / COUNTROWS(fact_interaction)` |
| Total contact cost | 總聯絡成本 | `SUM(cost_mop)` |
| Cost per case | 每個案成本 | `SUM(cost_mop) / DISTINCTCOUNT(case_id)` |

## Backlog

| Metric | 中文 | Formula | Notes |
|---|---|---|---|
| Open backlog | 待處理積壓 | `contacts with is_open = TRUE` | As of the data snapshot |
| Oldest open (days) | 最舊積壓天數 | `MAX(age_days)` where open | `age_days` is snapshot-based |
| Aging buckets | 積壓帳齡 | `0-1d / 1-3d / 3-7d / 7-14d / 14-30d / 30d+` | Bucket the **live** age `DATEDIFF(start_ts, TODAY(), DAY)` in Power BI so the dashboard stays current |

## Judgement calls worth defending in an interview

0. **DAX blank coercion is a trap** — `BLANK() <= 6` evaluates to **TRUE** in DAX (blank is coerced to 0 for
   numeric comparison). The first version of the NPS measures therefore counted every non-responded contact
   as a detractor and produced −433 instead of +11.6. Every NPS measure now filters
   `fact_interaction[responded] = TRUE ()` explicitly. The pandas reference never had this bug (NaN
   comparisons are False), which is exactly why the dashboard is validated against it.
1. **FCR is defined by outcome, not by a checkbox** — a case counts as first-contact resolved only if it
   closed on contact 1 of the series; contacts are linked into series by `case_id`.
2. **Abandoned contacts are excluded from SLA and experience denominators.** They are counted in demand
   and cost.
3. **NPS is a proportion difference, not a mean.** Bootstrapping it for a confidence interval is the
   correct treatment; a ±3 point NPS move on n=400 is noise.
4. **Response rate is reported next to every satisfaction figure** — a 27% response rate can be
   systematically biased toward angry or delighted customers.
5. **This dataset is synthetic.** The generator plants known effects (see `src/generate_data.py`) so the
   method can be validated; the numbers are not evidence about any real organisation.
