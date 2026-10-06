# DAX measures — paste-ready

Create a **measures table** (Enter Data → name it `_Measures`, hide its column) or put these in
`fact_interaction`. Use display folders so the model stays navigable.

Conventions used below: `TRUE()` / `FALSE()` are DAX booleans; `DIVIDE()` is used everywhere to avoid
divide-by-zero. Percentages are formatted `0.0%`, NPS as `+0;-0;0`.

```dax
-- ===== Base counts =====
Contacts = COUNTROWS ( fact_interaction )

Cases = DISTINCTCOUNT ( fact_interaction[case_id] )

Answered contacts =
CALCULATE ( [Contacts], fact_interaction[is_answered] = TRUE () )

Abandoned contacts =
CALCULATE ( [Contacts], fact_interaction[is_abandoned] = TRUE () )

Closing contacts =
CALCULATE ( [Contacts], fact_interaction[is_closing_contact] = TRUE () )

Responded surveys =
CALCULATE ( [Contacts], fact_interaction[responded] = TRUE () )
```

```dax
-- ===== Demand / efficiency =====
Contacts per case =
DIVIDE ( [Contacts], [Cases] )

Abandonment % =
DIVIDE ( [Abandoned contacts], [Contacts] )

Repeat contact % =
DIVIDE (
    CALCULATE ( [Contacts], fact_interaction[contact_seq] > 1 ),
    [Contacts]
)
```

```dax
-- ===== Service level and speed =====
SLA % =
DIVIDE (
    CALCULATE ( [Contacts], fact_interaction[is_within_sla] = TRUE () ),
    [Answered contacts]
)

ASA seconds =
CALCULATE (
    AVERAGE ( fact_interaction[wait_seconds] ),
    dim_channel[is_synchronous] = TRUE (),
    fact_interaction[is_answered] = TRUE ()
)

First response hours =
CALCULATE (
    DIVIDE ( AVERAGE ( fact_interaction[wait_seconds] ), 3600 ),
    dim_channel[is_synchronous] = FALSE (),
    fact_interaction[is_answered] = TRUE ()
)

AHT seconds =
CALCULATE (
    AVERAGE ( fact_interaction[handle_seconds] ),
    fact_interaction[is_answered] = TRUE ()
)

AHT minutes = DIVIDE ( [AHT seconds], 60 )
```

```dax
-- ===== Resolution quality =====
FCR % =
DIVIDE (
    CALCULATE (
        DISTINCTCOUNT ( fact_interaction[case_id] ),
        fact_interaction[is_first_contact_resolved] = TRUE ()
    ),
    [Cases]
)

Escalation % =
DIVIDE (
    CALCULATE (
        DISTINCTCOUNT ( fact_interaction[case_id] ),
        fact_interaction[is_escalated] = TRUE ()
    ),
    [Cases]
)

Avg transfers =
CALCULATE ( AVERAGE ( fact_interaction[transfer_count] ), fact_interaction[is_answered] = TRUE () )
```

```dax
-- ===== Experience (denominator is always responded surveys) =====
Response rate % =
DIVIDE ( [Responded surveys], [Closing contacts] )

CSAT top-box % =
DIVIDE (
    CALCULATE ( [Contacts], fact_interaction[csat_score] >= 4 ),
    [Responded surveys]
)

CSAT mean =
CALCULATE ( AVERAGE ( fact_interaction[csat_score] ), fact_interaction[responded] = TRUE () )

CES mean =
CALCULATE ( AVERAGE ( fact_interaction[ces_score] ), fact_interaction[responded] = TRUE () )

CES % easy =
DIVIDE (
    CALCULATE ( [Contacts], fact_interaction[ces_score] >= 5 ),
    [Responded surveys]
)

Promoters = CALCULATE ( [Contacts], fact_interaction[responded] = TRUE (), fact_interaction[nps_score] >= 9 )
Passives  = CALCULATE ( [Contacts], fact_interaction[responded] = TRUE (), fact_interaction[nps_score] >= 7 && fact_interaction[nps_score] <= 8 )
Detractors = CALCULATE ( [Contacts], fact_interaction[responded] = TRUE (), fact_interaction[nps_score] <= 6 )

NPS =
DIVIDE ( [Promoters] - [Detractors], [Responded surveys] ) * 100
```

```dax
-- ===== Cost =====
Cost per contact = DIVIDE ( SUM ( fact_interaction[cost_mop] ), [Contacts] )
Cost per case    = DIVIDE ( SUM ( fact_interaction[cost_mop] ), [Cases] )
Total cost       = SUM ( fact_interaction[cost_mop] )
```

```dax
-- ===== Backlog =====
Open backlog =
CALCULATE ( [Contacts], fact_interaction[is_open] = TRUE () )

Oldest open days =
CALCULATE ( MAX ( fact_interaction[age_days] ), fact_interaction[is_open] = TRUE () )

Open age days (live) =
IF (
    fact_interaction[is_open],
    DATEDIFF ( fact_interaction[start_ts], TODAY (), DAY )
)

Backlog older than 7 days =
CALCULATE (
    [Contacts],
    fact_interaction[is_open] = TRUE (),
    FILTER ( fact_interaction, DATEDIFF ( fact_interaction[start_ts], TODAY (), DAY ) > 7 )
)
```

```dax
-- ===== Time intelligence (requires dim_date marked as date table) =====
SLA % (last 4 weeks) =
CALCULATE ( [SLA %], DATESINPERIOD ( dim_date[date], MAX ( dim_date[date] ), -28, DAY ) )

CSAT mean (last 4 weeks) =
CALCULATE ( [CSAT mean], DATESINPERIOD ( dim_date[date], MAX ( dim_date[date] ), -28, DAY ) )

Contacts 7-day average =
AVERAGEX ( DATESINPERIOD ( dim_date[date], MAX ( dim_date[date] ), -7, DAY ), [Contacts] )

Contacts vs previous week =
VAR CurrentWeek = [Contacts]
VAR PrevWeek =
    CALCULATE ( [Contacts], DATEADD ( dim_date[date], -7, DAY ) )
RETURN DIVIDE ( CurrentWeek - PrevWeek, PrevWeek )
```

```dax
-- ===== Dynamic titles / annotations used on the report =====
SLA subtitle =
VAR W = SELECTEDVALUE ( dim_date[week_index] )
RETURN "Week " & W & " — attainment " & FORMAT ( [SLA %], "0.0%" )
    & " vs target " & FORMAT ( DIVIDE ( [Answered contacts], [Contacts] ) * 0 + 0.90, "0%" )
```

## Formatting and display

| Measure | Format string |
|---|---|
| `SLA %`, `FCR %`, `Abandonment %`, `Repeat contact %`, `Escalation %`, `CSAT top-box %`, `CES % easy`, `Response rate %` | `0.0%` |
| `CSAT mean` | `0.00` |
| `CES mean` | `0.00` |
| `NPS` | `+0;-0;0` |
| `ASA seconds`, `AHT seconds`, `Oldest open days` | `#,##0` |
| `First response hours` | `0.0 "h"` |
| `Cost per contact`, `Cost per case` | `"MOP " #,##0.00` |
| `Total cost` | `"MOP " #,##0` |

## Conditional formatting that earns its place

- **SLA %** card: font colour — red below 0.80, amber 0.80–0.90, green ≥ 0.90. Threshold, not decoration.
- **CES % easy / CSAT top-box %**: same traffic-light pattern.
- **Open age days (live)** in the backlog table: data bars, with the 7-day column flagged red.

## Validation — the DAX must reproduce these numbers

Run `python src/kpi_reference.py` and compare against the dashboard (whole dataset, no slicers):

| Metric | Reference value |
|---|---|
| Contacts | 23,162 |
| Cases | 15,721 |
| Contacts per case | 1.47 |
| Answered contacts | 22,193 |
| Abandonment % | 4.2% |
| SLA % | 58.7% |
| ASA seconds (real-time) | 73 |
| First response hours (async) | 4.3 |
| AHT seconds | 336 |
| FCR % | 62.0% |
| Repeat contact % | 32.1% |
| Escalation % | 11.6% |
| Response rate % | 27.1% |
| CSAT top-box % | 71.2% |
| CSAT mean | 3.99 |
| CES mean | 4.84 |
| CES % easy | 61.3% |
| NPS | +11.6 (41.7% promoters, 30.1% detractors) |
| Cost per contact | MOP 13.14 |
| Total cost | MOP 304,462 |
| Open backlog | 431 |
| Oldest open days | 46 |

If a number differs, the usual causes are: (a) a measure missing the `responded = TRUE` filter,
(b) computing FCR at contact grain, (c) including abandoned contacts in the SLA denominator,
(d) averaging ASA across sync and async channels.
