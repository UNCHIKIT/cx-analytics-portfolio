"""Python equivalents of every procedure in analysis/cx_metrics.sps.

Design intent: the SPSS syntax and this script must produce the SAME numbers from the
SAME file (data/cx_survey.sav). This file is the answer key the SPSS output is checked
against — SPSS cannot be run on this machine (no licence), so an independent
implementation is how the numbers stay verifiable.

Run:  python src/spss_equivalent.py
Out:  outputs/spss_equivalence.md  (tables)
      outputs/spss_results.json    (machine-readable, feeds the findings report)
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyreadstat
from scipy import stats
from statsmodels.miscmodels.ordinal_model import OrderedModel
from statsmodels.stats.oneway import anova_oneway
from statsmodels.stats.multicomp import pairwise_tukeyhsd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "outputs"
SEED = 20261005
BOOTSTRAP_SAMPLES = 2000

R = {}          # results collected for the report
LINES: list[str] = []


def sec(title: str) -> None:
    LINES.append("")
    LINES.append(f"## {title}")
    LINES.append("")


def table(rows: list[list[str]], header: list[str]) -> None:
    LINES.append("| " + " | ".join(header) + " |")
    LINES.append("|" + "|".join("---" for _ in header) + "|")
    for r in rows:
        LINES.append("| " + " | ".join(str(x) for x in r) + " |")
    LINES.append("")


def main() -> int:
    OUT.mkdir(exist_ok=True)
    df, meta = pyreadstat.read_sav(str(DATA / "cx_survey.sav"))
    n = len(df)
    LINES.append("# SPSS ⇄ Python equivalence — CX survey analysis")
    LINES.append("")
    LINES.append(f"Source file: `data/cx_survey.sav` — {n:,} responded post-contact surveys, 26 weeks, "
                 f"{df.shape[1]} variables. Every figure below is computed by this script and must match "
                 f"the corresponding SPSS procedure in `analysis/cx_metrics.sps`.")
    R["n"] = int(n)

    # ---------------------------------------------------------------- 1. metrics
    sec("1. CX metrics — FREQUENCIES / DESCRIPTIVES (syntax §2)")
    promoter = (df["nps"] >= 9).mean()
    detractor = (df["nps"] <= 6).mean()
    nps_points = (promoter - detractor) * 100
    rows = []
    for var, label in [("csat", "CSAT (1-5)"), ("ces", "CES (1-7)"), ("nps", "NPS item (0-10)")]:
        s = df[var]
        rows.append([label, f"{s.mean():.2f}", f"{s.std(ddof=1):.2f}", f"{s.min():.0f}", f"{s.max():.0f}"])
    table(rows, ["Variable", "Mean", "SD", "Min", "Max"])
    table([
        ["Promoters (9-10)", f"{promoter:.1%}"],
        ["Detractors (0-6)", f"{detractor:.1%}"],
        ["**NPS (points)**", f"**{nps_points:+.1f}**"],
        ["CSAT top-box (4-5)", f"{(df['csat'] >= 4).mean():.1%}"],
        ["CES % easy (5-7)", f"{(df['ces'] >= 5).mean():.1%}"],
    ], ["Metric", "Value"])
    R["metrics"] = {"promoter": promoter, "detractor": detractor, "nps_points": nps_points,
                    "csat_top_box": float((df["csat"] >= 4).mean()),
                    "ces_easy": float((df["ces"] >= 5).mean()),
                    "csat_mean": float(df["csat"].mean()), "ces_mean": float(df["ces"].mean())}

    # ---------------------------------------------------------------- 2. bootstrap NPS
    sec("2. Bootstrap CI for NPS — BOOTSTRAP /SAMPLES=2000 (syntax §3)")
    rng = np.random.default_rng(SEED)
    nps_scores = df["nps"].to_numpy()
    boots = np.empty(BOOTSTRAP_SAMPLES)
    for b in range(BOOTSTRAP_SAMPLES):
        sample = rng.choice(nps_scores, size=n, replace=True)
        boots[b] = (sample >= 9).mean() * 100 - (sample <= 6).mean() * 100
    lo, hi = np.percentile(boots, [2.5, 97.5])
    table([["NPS point estimate", f"{nps_points:+.1f}"],
           ["Bootstrap 95% CI (2,000 resamples, seed 20261005)", f"[{lo:+.1f}, {hi:+.1f}]"],
           ["Bootstrap SE", f"{boots.std(ddof=1):.1f}"]],
          ["Statistic", "Value"])
    R["nps_ci"] = [float(lo), float(hi)]

    # ---------------------------------------------------------------- 3. chi-square
    sec("3. NPS mix × channel — CROSSTABS /STATISTICS=CHISQ PHI (syntax §4)")
    ct = pd.crosstab(df["channel"], df["nps_group"])
    chi2, p, dof, _ = stats.chi2_contingency(ct)
    cramers_v = math_sqrt(chi2 / (n * (min(ct.shape) - 1)))
    LINES.append("Observed counts (rows = channel, columns = 1 Detractor / 2 Passive / 3 Promoter):")
    LINES.append("")
    table([[idx] + [f"{v:,}" for v in row] for idx, row in zip(ct.index, ct.to_numpy())],
          ["Channel", "Detractor", "Passive", "Promoter"])
    table([["Pearson chi-square", f"{chi2:.1f}", f"{dof}", f"{p:.3g}"],
           ["Cramér's V", f"{cramers_v:.3f}", "", ""]],
          ["Statistic", "Value", "df", "p"])
    R["chisq"] = {"chi2": float(chi2), "dof": int(dof), "p": float(p), "cramers_v": float(cramers_v)}

    # ---------------------------------------------------------------- 4. t-tests
    sec("4. Wait time by first-contact resolution — T-TEST (syntax §5)")
    df["log_wait"] = np.log1p(df["wait_seconds"])
    rows = []
    for var, label in [("wait_seconds", "wait_seconds (raw)"), ("log_wait", "ln(wait+1)")]:
        a = df.loc[df["first_contact_resolution"] == 1, var]
        b = df.loc[df["first_contact_resolution"] == 0, var]
        t, p = stats.ttest_ind(a, b, equal_var=False)
        diff = a.mean() - b.mean()
        se = np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
        rows.append([label, f"{a.mean():.3f}", f"{b.mean():.3f}", f"{diff:+.3f}",
                     f"[{diff - 1.96 * se:+.3f}, {diff + 1.96 * se:+.3f}]", f"{t:.2f}", f"{p:.3g}"])
        if var == "log_wait":
            R["ttest"] = {"mean_fcr": float(a.mean()), "mean_nofcr": float(b.mean()),
                          "diff": float(diff), "t": float(t), "p": float(p)}
    table(rows, ["Variable", "Mean (FCR=1)", "Mean (FCR=0)", "Difference", "95% CI", "t", "p"])
    LINES.append("`wait_seconds` means **queue wait** for real-time channels (Phone, Live Chat) but "
                 "**time to first response** for asynchronous channels (Email, Social Media, Web Form). "
                 "Pooling them is a channel confound, so the defensible test is within channel:")
    LINES.append("")
    rows = []
    for ch, g in df.groupby("channel"):
        a = g.loc[g["first_contact_resolution"] == 1, "log_wait"]
        b = g.loc[g["first_contact_resolution"] == 0, "log_wait"]
        if len(a) < 30 or len(b) < 30:
            continue
        t, p = stats.ttest_ind(a, b, equal_var=False)
        rows.append([ch, f"{len(g):,}", f"{a.mean():.2f}", f"{b.mean():.2f}",
                     f"{a.mean() - b.mean():+.2f}", f"{t:+.2f}", f"{p:.3g}"])
    table(rows, ["Channel", "n", "ln(wait) FCR=1", "ln(wait) FCR=0", "Difference", "t", "p"])

    # ---------------------------------------------------------------- 5. ANOVA
    sec("5. CSAT across service queues — ONEWAY (syntax §6) + robustness")
    groups = [g["csat"].to_numpy() for _, g in df.groupby("queue_num")]
    f, p_anova = stats.f_oneway(*groups)
    lev_w, lev_p = stats.levene(*groups, center="mean")
    welch = anova_oneway(groups, use_var="unequal")
    kw_h, kw_p = stats.kruskal(*groups)
    labels = df.groupby("queue_num")["queue"].first().to_dict()
    table([[f"{int(k)} {labels[k]}", f"{g['csat'].mean():.2f}", f"{g['csat'].std(ddof=1):.2f}", f"{len(g):,}"]
           for k, g in df.groupby("queue_num")],
          ["Queue", "Mean CSAT", "SD", "n"])
    table([["Classic ANOVA (F)", f"{f:.2f}", f"{p_anova:.3g}"],
           ["Welch ANOVA (heteroscedasticity-robust)", f"{welch.statistic:.2f}", f"{welch.pvalue:.3g}"],
           ["Levene test (equal variances?)", f"{lev_w:.2f}", f"{lev_p:.3g}"],
           ["Kruskal-Wallis (non-parametric)", f"{kw_h:.2f}", f"{kw_p:.3g}"]],
          ["Test", "Statistic", "p"])
    tukey = pairwise_tukeyhsd(df["csat"], df["queue_num"])
    # result rows are [group1, group2, meandiff, p-adj, lower, upper, reject]
    sig = [(f"{labels[int(r[0])]} vs {labels[int(r[1])]}", f"{r[2]:+.2f}", f"{r[3]:.3g}")
           for r in tukey._results_table.data[1:] if bool(r[6])]
    total_pairs = len(tukey._results_table.data) - 1
    LINES.append(f"Tukey HSD: {len(sig)} of {total_pairs} pairs differ at p<0.05. Largest gaps "
                 "(by absolute difference):")
    LINES.append("")
    sig_sorted = sorted(sig, key=lambda x: -abs(float(x[1])))
    table(sig_sorted[:5], ["Pair", "Mean difference", "p (adjusted)"])
    R["anova"] = {"f": float(f), "p": float(p_anova), "welch_p": float(welch.pvalue),
                  "lev_p": float(lev_p), "kw_p": float(kw_p),
                  "queue_means": {labels[k]: float(g["csat"].mean()) for k, g in df.groupby("queue_num")}}

    # ---------------------------------------------------------------- 6. regression
    sec("6. Driver analysis — REGRESSION with standardised betas (syntax §7)")
    preds = ["log_wait", "first_contact_resolution", "escalated", "transfer_count"]
    X = df[preds].astype(float)
    y = df["csat"].astype(float)
    model = sm_ols(y, X)
    both = pd.concat([X, y], axis=1)
    z = (both - both.mean()) / both.std(ddof=1)      # SPSS Beta = coefficients on z-scores
    zm = sm_ols(z["csat"], z[preds])
    rows = []
    for name in preds:                                # name-based lookups: no off-by-one with the constant
        rows.append([name, f"{model.params[name]:+.3f}", f"{model.bse[name]:.3f}",
                     f"{model.tvalues[name]:+.2f}", f"{model.pvalues[name]:.3g}",
                     f"{zm.params[name]:+.3f}"])
    table(rows, ["Predictor", "B (unstd.)", "SE", "t", "p", "Beta (std.)"])
    table([["Constant", f"{model.params['const']:+.3f}"],
           ["R²", f"{model.rsquared:.3f}"],
           ["Adjusted R²", f"{model.rsquared_adj:.3f}"],
           ["F / p", f"{model.fvalue:.1f} / {model.f_pvalue:.3g}"],
           ["n", f"{int(model.nobs):,}"]],
          ["Model fit", "Value"])
    R["regression"] = {"r2": float(model.rsquared), "adj_r2": float(model.rsquared_adj),
                       "f": float(model.fvalue), "p": float(model.f_pvalue),
                       "betas": {k: float(zm.params[k]) for k in preds},
                       "bs": {k: float(model.params[k]) for k in preds},
                       "ps": {k: float(model.pvalues[k]) for k in preds}}
    strongest = max(preds, key=lambda k: abs(R["regression"]["betas"][k]))

    # ---------------------------------------------------------------- 7. ordinal
    sec("7. Ordinal logistic regression — PLUM (syntax §8)")
    om = OrderedModel(df["csat"].astype(float), df[preds].astype(float), distr="logit")
    res = om.fit(method="bfgs", disp=False)
    names = preds + [f"threshold {k}" for k in sorted(df["csat"].unique())[1:]]
    table([[names[i], f"{res.params.iloc[i]:+.3f}", f"{res.bse.iloc[i]:.3f}", f"{res.tvalues.iloc[i]:+.2f}",
            f"{res.pvalues.iloc[i]:.3g}"] for i in range(len(res.params))],
          ["Parameter", "Coefficient (log-odds)", "SE", "z", "p"])
    LINES.append("Note: SPSS `PLUM … /PRINT=TPARALLEL` also reports the test of parallel lines "
                 "(proportional-odds assumption); statsmodels has no direct equivalent, so that test "
                 "is only available from the SPSS run.")
    R["ordinal"] = {"coefs": {names[i]: float(res.params.iloc[i]) for i in range(len(preds))},
                    "ps": {names[i]: float(res.pvalues.iloc[i]) for i in range(len(preds))}}

    # ---------------------------------------------------------------- write
    (OUT / "spss_equivalence.md").write_text("\n".join(LINES) + "\n", encoding="utf-8")
    (OUT / "spss_results.json").write_text(json.dumps(R, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"n = {R['n']:,}")
    print(f"NPS = {R['metrics']['nps_points']:+.1f}  95% CI [{R['nps_ci'][0]:+.1f}, {R['nps_ci'][1]:+.1f}]")
    print(f"chi-square = {R['chisq']['chi2']:.1f} (df {R['chisq']['dof']}, p = {R['chisq']['p']:.3g}), "
          f"Cramer's V = {R['chisq']['cramers_v']:.3f}")
    print(f"ANOVA F = {R['anova']['f']:.2f} (p = {R['anova']['p']:.3g}); "
          f"Welch p = {R['anova']['welch_p']:.3g}; Levene p = {R['anova']['lev_p']:.3g}")
    print(f"Regression R2 = {R['regression']['r2']:.3f}; strongest standardised driver: {strongest} "
          f"(Beta {R['regression']['betas'][strongest]:+.2f}, p = {R['regression']['ps'][strongest]:.3g})")
    print("wrote outputs/spss_equivalence.md, outputs/spss_results.json")
    return 0


def math_sqrt(x: float) -> float:
    return float(np.sqrt(max(x, 0.0)))


def sm_ols(y: pd.Series, X: pd.DataFrame):
    import statsmodels.api as sm
    return sm.OLS(y, sm.add_constant(X)).fit()


if __name__ == "__main__":
    raise SystemExit(main())
