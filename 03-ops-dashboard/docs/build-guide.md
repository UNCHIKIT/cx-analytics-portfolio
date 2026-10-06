# Build guide — Power BI Desktop (~45 minutes, click by click)

Everything except the clicking is already done: the CSVs are generated, the model is specified, the
measures are written, and the reference numbers are computed so you can prove the dashboard is correct.
Power BI Desktop is free: `winget install --id Microsoft.PowerBI` (or
<https://www.microsoft.com/download/details.aspx?id=58494>).

## MVP path first (30 minutes) — 先做 MVP

**MVP = 一頁報表 + 8 條度量值 + 數字核對 + 截圖 + Publish 連結. 做到這樣就已經可以投遞。**
以下第 1–3 節照做，第 4 節只做「Page 1」，然後跳去第 6 節核對數字、第 5 節只做 Publish 與截圖。

**MVP 必須保留（唔可以省）**

| 必須 | 原因 |
|---|---|
| 度量值的篩選條件正確（`responded = TRUE`；FCR 用個案粒度；SLA 分母只算已接聽；ASA 只算即時渠道） | 這是「你懂不懂指標」的證據，錯一條就前功盡棄 |
| 與 `outputs/kpi_reference.md` 核對 22 個數字 | 證明你的 Power BI 數字可信，不是「看起來差不多」 |
| 一頁報表 + 截圖 + 發佈連結 | HR／面試官不會開 `.pbix` |
| README 的「Impact & limits」一段 | 資深與否的分界線 |

**MVP 可以省（列為「後補」）**

| 省略項 | 何時再補 |
|---|---|
| Page 2 / Page 3、下鑽、scatter、動態標題 | 有面試邀約後 |
| 排程重新整理 + on-premises gateway | 只在面試被問「你會怎麼自動化」時口頭講 + 補 |
| RLS 角色 | 同上 |
| `dim_customer` / `dim_agent` 的深入視覺 | 非 JD 必要 |

**MVP 完成定義（Definition of Done）**：打開 `.pbix` 見到一頁報表、8 條度量值數字與參考值一致、
已 Publish、截圖已存 `outputs/screens/`、你能不看稿講 90 秒（第 7 節）。**到此停止。**

---

## 1. Load the data

1. **Home → Get data → Text/CSV**, one file at a time from `03-ops-dashboard/data/`:
   `fact_interaction.csv`, `dim_date.csv`, `dim_channel.csv`, `dim_queue.csv`, `dim_agent.csv`,
   `dim_customer.csv`, `dim_status.csv`.
2. In each preview window: **Data type detection = Do not detect types** → **Transform Data** (not Load).
   You will set types explicitly — auto-detection turns `date_key` into a number and `interaction_id`
   into a number and breaks relationships.

## 2. Transform (Power Query)

For **fact_interaction**, set these types:

| Column | Type |
|---|---|
| `interaction_id`, `status` | Text |
| `case_id`, `customer_id`, `agent_id`, `channel_id`, `queue_id`, `date_key`, `week_index`, `hour_of_day`, `contact_seq`, `case_contact_count`, `wait_seconds`, `talk_seconds`, `wrap_seconds`, `handle_seconds`, `transfer_count`, `sla_target_seconds`, `csat_score`, `ces_score`, `nps_score` | Whole number |
| `start_ts`, `end_ts` | Date/Time |
| `age_days`, `cost_mop` | Decimal number |
| `is_first_contact_resolved`, `is_repeat_contact`, `is_answered`, `is_abandoned`, `is_open`, `is_escalated`, `is_within_sla`, `responded` | True/False |

For **dim_date**: `date` → Date, `week_start_date` → Date, `date_key`/`year`/`quarter`/`month`/
`week_index`/`weekday_num` → Whole number, rest Text.
For **dim_channel**: `channel_id` Whole number, `is_synchronous` True/False, `unit_cost_mop` Decimal,
`sla_target_seconds` Whole number.
For **dim_queue**: `queue_id` Whole number, `satisfaction_offset` Decimal.
For **dim_agent** / **dim_customer**: ids and `tenure_months` Whole number, `is_new_customer` True/False.

**Close & Apply.**

### Optional but recommended for a live demo
**Home → Get data → Folder** pointed at `data/` and filter to `fact_*.csv` gives you the "add a new file
and refresh" story. For a first build, individual CSVs are simpler.

## 3. Model

1. **Model view** → drag relationships (should auto-detect the five joins; fix cardinality to
   Many-to-one, cross-filter Single):

| From | To |
|---|---|
| `fact_interaction[date_key]` | `dim_date[date_key]` |
| `fact_interaction[channel_id]` | `dim_channel[channel_id]` |
| `fact_interaction[queue_id]` | `dim_queue[queue_id]` |
| `fact_interaction[agent_id]` | `dim_agent[agent_id]` |
| `fact_interaction[customer_id]` | `dim_customer[customer_id]` |
| `fact_interaction[status]` | `dim_status[status]` |

2. Mark the date table: select `dim_date` → **Table tools → Mark as date table → `date`**.
3. Add the one calculated column the response-rate measure needs:
   `fact_interaction` → New column → `is_closing_contact = fact_interaction[contact_seq] = fact_interaction[case_contact_count]`
4. Hide every key (`*_id`, `date_key`) and the `_Measures` placeholder column.
5. Create the measures: **Modeling → New measure**, paste each block from `docs/dax-measures.md`,
   set the format string, and put them in display folders (Service level / Resolution / Experience /
   Cost / Backlog).

## 4. Report — three pages

**Page 1 · Service operations (executive)**
- Cards: `Contacts`, `SLA %`, `FCR %`, `AHT minutes`, `Abandonment %`, `Cost per contact`.
- Line + clustered column over `dim_date[week_start_date]`: columns = `Contacts`, line = `SLA %`.
- Matrix: rows `dim_queue[queue]`, columns `dim_channel[channel]`, values `Contacts` (+ conditional
  formatting on `SLA %` as the tooltip).
- Slicers: `dim_date[week_index]`, `dim_queue[queue]`, `dim_channel[channel]`.

**Page 2 · Experience (voice of the customer)**
- Cards: `CSAT top-box %`, `CES % easy`, `NPS`, `Response rate %` — put response rate next to NPS, always.
- Line: `CSAT mean`, `CES mean` by week; second axis or tooltip for `NPS`.
- Bar: `CSAT mean` by `dim_queue[queue]` with `NPS` as a tooltip.
- Scatter: `AVERAGE(wait_seconds)` (X) vs `CSAT mean` (Y) by channel, filtered to
  `dim_channel[is_synchronous] = TRUE` — the point is the negative slope (r ≈ −0.49).
- Note in a text box: *"Survey sent on the closing contact of each case; satisfaction figures cover
  responded surveys only."*

**Page 3 · Backlog and aging**
- Cards: `Open backlog`, `Oldest open days`, `Backlog older than 7 days`.
- Stacked column: aging bucket (calculated column on `Open age days (live)`) by `dim_channel[channel]`.
- Table: `interaction_id`, `channel`, `queue`, `start_ts`, `Open age days (live)` filtered to open,
  sorted descending, with data bars.
- Drill-through from Page 1 on `dim_queue[queue]`.

## 5. Publish, refresh, secure

1. **Home → Publish** to a workspace (My workspace is fine for the CV link).
2. **Semantic model → Settings → Scheduled refresh**: daily at 06:00. For a real CSV-on-disk source you
   need an on-premises data gateway; with OneDrive/SharePoint or Azure Blob storage you can refresh
   cloud-side without one.
3. **Roles**: Model view → Manage roles → `Team Lead` filtering `dim_agent[team]`. Test with
   *View as role*. (Full RLS pattern in `docs/data-model.md`.)
4. **Screenshot every page** into `outputs/screens/` — HR and most interviewers will not open a `.pbix`.

## 6. Prove it is correct

Run `python src/kpi_reference.py`, then compare the dashboard's whole-dataset values against the table at
the bottom of `docs/dax-measures.md`. They must match exactly; `outputs/kpi_reference.md` holds the full
reference. If they do not, the four usual causes are listed there.

## 7. What to say about it (90-second interview story)

> "23,162 contacts over 26 weeks across five channels. I modelled it as a star schema with contact-grain
> facts and case-level resolution flags, because FCR and repeat-contact rate are case metrics and most
> dashboards get that wrong. Two things fell out of it: phone wait time doubled from week 14 after a
> staffing gap, and phone CES fell 1.11 points (p < 0.001) while email first-response SLA collapsed from
> 81% to 24% from week 23 because the backlog was never worked down. I separated that from a false
> signal — Billing contact volume doubled in weeks 18–19 from a campaign with no satisfaction change, so
> volume alone would have sent the team to the wrong queue. Priority one is the email backlog, priority
> two is phone staffing, and both are measurable: SLA attainment and CES are the two lead indicators."
