# SPSS ⇄ Python equivalence — CX survey analysis

Source file: `data/cx_survey.sav` — 4,256 responded post-contact surveys, 26 weeks, 26 variables. Every figure below is computed by this script and must match the corresponding SPSS procedure in `analysis/cx_metrics.sps`.

## 1. CX metrics — FREQUENCIES / DESCRIPTIVES (syntax §2)

| Variable | Mean | SD | Min | Max |
|---|---|---|---|---|
| CSAT (1-5) | 3.99 | 0.95 | 1 | 5 |
| CES (1-7) | 4.84 | 1.36 | 1 | 7 |
| NPS item (0-10) | 7.59 | 2.21 | 0 | 10 |

| Metric | Value |
|---|---|
| Promoters (9-10) | 41.7% |
| Detractors (0-6) | 30.1% |
| **NPS (points)** | **+11.6** |
| CSAT top-box (4-5) | 71.2% |
| CES % easy (5-7) | 61.3% |


## 2. Bootstrap CI for NPS — BOOTSTRAP /SAMPLES=2000 (syntax §3)

| Statistic | Value |
|---|---|
| NPS point estimate | +11.6 |
| Bootstrap 95% CI (2,000 resamples, seed 20261005) | [+9.1, +14.0] |
| Bootstrap SE | 1.3 |


## 3. NPS mix × channel — CROSSTABS /STATISTICS=CHISQ PHI (syntax §4)

Observed counts (rows = channel, columns = 1 Detractor / 2 Passive / 3 Promoter):

| Channel | Detractor | Passive | Promoter |
|---|---|---|---|
| Email | 226 | 288 | 468 |
| Live Chat | 200 | 267 | 555 |
| Phone | 780 | 563 | 630 |
| Social Media | 48 | 56 | 71 |
| Web Form | 27 | 28 | 49 |

| Statistic | Value | df | p |
|---|---|---|---|
| Pearson chi-square | 209.7 | 8 | 5.65e-41 |
| Cramér's V | 0.157 |  |  |


## 4. Wait time by first-contact resolution — T-TEST (syntax §5)

| Variable | Mean (FCR=1) | Mean (FCR=0) | Difference | 95% CI | t | p |
|---|---|---|---|---|---|---|
| wait_seconds (raw) | 4759.708 | 3633.458 | +1126.250 | [+577.903, +1674.597] | 4.03 | 5.8e-05 |
| ln(wait+1) | 5.816 | 5.427 | +0.388 | [+0.240, +0.537] | 5.12 | 3.23e-07 |

`wait_seconds` means **queue wait** for real-time channels (Phone, Live Chat) but **time to first response** for asynchronous channels (Email, Social Media, Web Form). Pooling them is a channel confound, so the defensible test is within channel:

| Channel | n | ln(wait) FCR=1 | ln(wait) FCR=0 | Difference | t | p |
|---|---|---|---|---|---|---|
| Email | 982 | 9.26 | 9.23 | +0.03 | +0.61 | 0.541 |
| Live Chat | 1,022 | 4.01 | 4.12 | -0.12 | -3.07 | 0.00223 |
| Phone | 1,973 | 4.13 | 4.18 | -0.04 | -1.51 | 0.131 |
| Social Media | 175 | 9.51 | 9.62 | -0.11 | -1.38 | 0.17 |
| Web Form | 104 | 9.80 | 9.94 | -0.14 | -1.38 | 0.171 |


## 5. CSAT across service queues — ONEWAY (syntax §6) + robustness

| Queue | Mean CSAT | SD | n |
|---|---|---|---|
| 1 Account Management | 4.22 | 0.85 | 842 |
| 2 Billing | 4.10 | 0.88 | 1,152 |
| 3 Complaints & Escalations | 3.29 | 1.04 | 466 |
| 4 Delivery & Logistics | 3.97 | 0.94 | 565 |
| 5 Technical Support | 4.01 | 0.94 | 1,231 |

| Test | Statistic | p |
|---|---|---|
| Classic ANOVA (F) | 84.77 | 2.28e-69 |
| Welch ANOVA (heteroscedasticity-robust) | 71.65 | 4.05e-56 |
| Levene test (equal variances?) | 6.10 | 6.84e-05 |
| Kruskal-Wallis (non-parametric) | 270.98 | 1.96e-57 |

Tukey HSD: 8 of 10 pairs differ at p<0.05. Largest gaps (by absolute difference):

| Pair | Mean difference | p (adjusted) |
|---|---|---|
| Account Management vs Complaints & Escalations | -0.93 | 0 |
| Billing vs Complaints & Escalations | -0.81 | 0 |
| Complaints & Escalations vs Technical Support | +0.72 | 0 |
| Complaints & Escalations vs Delivery & Logistics | +0.68 | 0 |
| Account Management vs Delivery & Logistics | -0.24 | 0 |


## 6. Driver analysis — REGRESSION with standardised betas (syntax §7)

| Predictor | B (unstd.) | SE | t | p | Beta (std.) |
|---|---|---|---|---|---|
| log_wait | -0.017 | 0.005 | -3.56 | 0.000373 | -0.044 |
| first_contact_resolution | +0.952 | 0.024 | +38.95 | 5.09e-284 | +0.486 |
| escalated | -0.704 | 0.042 | -16.77 | 3.35e-61 | -0.235 |
| transfer_count | -0.148 | 0.020 | -7.55 | 5.46e-14 | -0.106 |

| Model fit | Value |
|---|---|
| Constant | +3.653 |
| R² | 0.347 |
| Adjusted R² | 0.346 |
| F / p | 564.1 / 0 |
| n | 4,256 |


## 7. Ordinal logistic regression — PLUM (syntax §8)

| Parameter | Coefficient (log-odds) | SE | z | p |
|---|---|---|---|---|
| log_wait | -0.049 | 0.012 | -4.18 | 2.93e-05 |
| first_contact_resolution | +2.223 | 0.068 | +32.68 | 2.97e-234 |
| escalated | -1.545 | 0.105 | -14.68 | 8.38e-49 |
| transfer_count | -0.358 | 0.048 | -7.42 | 1.21e-13 |
| threshold 2.0 | -4.791 | 0.177 | -27.06 | 2.89e-161 |
| threshold 3.0 | +0.810 | 0.067 | +12.09 | 1.26e-33 |
| threshold 4.0 | +0.745 | 0.031 | +23.79 | 3.9e-125 |
| threshold 5.0 | +0.698 | 0.024 | +29.07 | 7.64e-186 |

Note: SPSS `PLUM … /PRINT=TPARALLEL` also reports the test of parallel lines (proportional-odds assumption); statsmodels has no direct equivalent, so that test is only available from the SPSS run.
