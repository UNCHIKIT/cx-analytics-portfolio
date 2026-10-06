* ===============================================================================.
* CX METRICS & DRIVER ANALYSIS - SPSS SYNTAX (portfolio piece A)
* Data      : cx_survey.sav  (4,256 responded post-contact surveys, 26 weeks,
*             26 variables, value labels and measure levels attached)
* Reference : outputs/spss_equivalence.md - the same numbers computed independently
*             in Python from the same .sav; the two must agree.
* Requires  : SPSS Statistics 24+ (base + Advanced Statistics for PLUM).
* Codepage  : this file is intentionally plain ASCII so it opens in any locale.
* PSPP notes: BOOTSTRAP and PLUM are not supported by PSPP; everything else is.
* ===============================================================================.

* ---- 0. Open the data ---------------------------------------------------------.
GET FILE='cx_survey.sav'.
DATASET NAME cx WINDOW=FRONT.

* ---- 1. Derived analysis variables -------------------------------------------.
* NPS groups follow the standard definition: promoters 9-10, detractors 0-6.
COMPUTE promoter = (nps GE 9).
COMPUTE detractor = (nps LE 6).
COMPUTE top_box_csat = (csat GE 4).
COMPUTE easy_ces = (ces GE 5).
* Wait times are right-skewed and mix queue-wait with first-response time,
* so the log transform is the analysis variable.
COMPUTE log_wait = LN(wait_seconds + 1).
EXECUTE.

* ---- 2. Level 1: the CX metrics themselves -----------------------------------.
* Expected: CSAT mean 3.99 (SD 0.95); CES mean 4.84 (SD 1.36); NPS item mean 7.59.
FREQUENCIES VARIABLES=csat ces nps
  /ORDER=ANALYSIS.
DESCRIPTIVES VARIABLES=csat ces nps
  /STATISTICS=MEAN STDDEV MIN MAX.

* NPS in POINTS = promoter% - detractor%.  Expected: +11.6
AGGREGATE
  /OUTFILE=* MODE=ADDVARIABLES
  /promoter_pct=MEAN(promoter)
  /detractor_pct=MEAN(detractor).
COMPUTE nps_points = (promoter_pct - detractor_pct) * 100.
DESCRIPTIVES VARIABLES=nps_points
  /STATISTICS=MEAN.

* Top-box and ease shares.  Expected: .712 and .613
DESCRIPTIVES VARIABLES=top_box_csat easy_ces
  /STATISTICS=MEAN.

* ---- 3. How precise is that NPS? (SPSS 20+; PSPP does not support BOOTSTRAP) ---.
* Expected 95% percentile CI: [+9.1, +14.0]  (2,000 resamples, seed 20261005)
BOOTSTRAP
  /SAMPLES=2000
  /SEED=20261005.
DESCRIPTIVES VARIABLES=promoter detractor
  /STATISTICS=MEAN.

* ---- 4. Is the NPS mix independent of channel? -------------------------------.
* Expected: chi-square 209.7, df 8, p < .001, Cramer's V .157
* Reading: channel and NPS group are NOT independent - Phone skews to detractors.
CROSSTABS
  /TABLES=channel BY nps_group
  /STATISTICS=CHISQ PHI
  /CELLS=COUNT ROW COLUMN.

* ---- 5. Wait time and first-contact resolution --------------------------------.
* Pooled test (shown for completeness - it is CONFOUNDED, see note below).
* Expected: ln(wait) t = 5.12, p < .001
T-TEST GROUPS=first_contact_resolution(0 1)
  /VARIABLES=wait_seconds log_wait
  /CRITERIA=CI(.95).

* The defensible version: wait means different things per channel
* (queue wait for Phone/Live Chat, time to first response for Email/Social/Web Form),
* so test WITHIN channel.
* Expected: only Live Chat is significant: t = -3.07, p = .002 (longer wait -> lower FCR).
SORT CASES BY channel_num.
SPLIT FILE LAYERED BY channel_num.
T-TEST GROUPS=first_contact_resolution(0 1)
  /VARIABLES=log_wait
  /CRITERIA=CI(.95).
SPLIT FILE OFF.

* ---- 6. Does CSAT differ across service queues? ------------------------------.
* Expected: F = 84.77, p < .001; Levene p < .001 (unequal variances) so the Welch
* and Kruskal-Wallis results are the ones to report:
*   Welch F = 71.65, p < .001; Kruskal-Wallis H = 270.98, p < .001
* Tukey: 8 of 10 pairs differ; Complaints & Escalations is the outlier
*   (Account Management 4.22 vs Complaints & Escalations 3.29; difference -0.93).
ONEWAY csat BY queue_num
  /STATISTICS=DESCRIPTIVES HOMOGENEITY WELCH
  /POSTHOC=TUKEY ALPHA(0.05)
  /MISSING=ANALYSIS.

NPAR TESTS
  /K-W=csat BY queue_num(1 5)
  /STATISTICS=DESCRIPTIVES.

* ---- 7. Driver analysis: what actually moves CSAT? ---------------------------.
* Standardised betas (Beta) rank the drivers.  Expected:
*   first_contact_resolution  B +0.952  Beta +0.486  p < .001   <- strongest
*   escalated                 B -0.704  Beta -0.235  p < .001
*   transfer_count            B -0.148  Beta -0.106  p < .001
*   log_wait                  B -0.017  Beta -0.044  p < .001
*   R2 = .347 (adjusted .346), F = 564.1
REGRESSION
  /DESCRIPTIVES MEAN STDDEV CORR SIG N
  /MISSING LISTWISE
  /STATISTICS=COEFF OUTS CI(95) R ANOVA CHANGE ZPP
  /CRITERIA=PIN(.05) POUT(.10)
  /NOORIGIN
  /DEPENDENT csat
  /METHOD=ENTER log_wait first_contact_resolution escalated transfer_count.

* Same model per service line (deep dive - which queue has a different driver set?).
SORT CASES BY queue_num.
SPLIT FILE LAYERED BY queue_num.
REGRESSION
  /STATISTICS=COEFF OUTS R ANOVA
  /DEPENDENT csat
  /METHOD=ENTER log_wait first_contact_resolution escalated transfer_count.
SPLIT FILE OFF.

* ---- 8. Ordinal logistic regression (CSAT is ordinal, not interval) ----------.
* PLUM respects the 1-5 ordering; expected coefficients (log-odds):
*   first_contact_resolution +2.223 (p < .001), escalated -1.545 (p < .001),
*   transfer_count -0.358 (p < .001), log_wait -0.049 (p < .001)
* /PRINT=TPARALLEL is the test of parallel lines - the proportional-odds check.
* It is reported by SPSS/PLUM only; the Python reference cannot reproduce it.
PLUM csat BY escalated first_contact_resolution WITH log_wait transfer_count
  /CRITERIA=CIN(95) DELTA(0) LCONVERGE(0) MXITER(100) MXSTEP(5) PCONVERGE(1.0E-6) SINGULAR(1.0E-8)
  /LINK=LOGIT
  /PRINT=FIT PARAMETER SUMMARY TPARALLEL.

* ---- 9. Optional: export the whole output for a report -----------------------.
* OUTPUT EXPORT /CONTENTS=ALL /DOCX DOCUMENTFILE='cx_spss_output.docx'.
