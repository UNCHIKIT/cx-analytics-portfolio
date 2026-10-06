"""Build the one-page portfolio summary (PDF-ready HTML) for job applications.

Pulls the verified artefacts from 03-ops-dashboard/outputs and writes
  portfolio/Portfolio_Summary_UnChiKit.html   (source of truth)
which is printed to PDF by Chromium and copied next to the CV.

Run:  python build_portfolio_onepager.py
"""

from __future__ import annotations

import base64
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DASH = ROOT / "03-ops-dashboard"
OUT = DASH / "outputs"
CV_FOLDER = Path("D:/REPO CV UNCHIKIT/01_Send_to_CEM/attachments")


def b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def img(path: Path, cls: str = "") -> str:
    if not path.exists():
        return ""
    return f'<img class="{cls}" src="data:image/png;base64,{b64(path)}">'


CSS = """
@page { size: A4; margin: 12mm 13mm; }
body { font-family: Calibri, "Segoe UI", Arial, sans-serif; font-size: 9.8pt; color: #16202b; line-height: 1.38; }
h1 { font-size: 17pt; color: #12456f; margin: 0 0 1mm 0; }
h2 { font-size: 11pt; color: #12456f; margin: 4mm 0 1.4mm 0; text-transform: uppercase;
     border-bottom: 1.2px solid #c3d3e4; padding-bottom: .7mm; }
.sub { color: #46586b; font-size: 9.4pt; margin: 0 0 .6mm 0; }
p { margin: 0 0 1.4mm 0; }
ul { margin: .6mm 0 1.6mm 5mm; padding: 0; }
li { margin-bottom: 1mm; }
.kpis { display: flex; gap: 2.5mm; margin: 2.5mm 0; }
.kpis div { flex: 1 1 0; border: 1px solid #c3d3e4; border-radius: 3px; padding: 1.6mm 2mm; text-align: center; }
.kpis .v { font-size: 12.5pt; font-weight: 700; color: #12456f; }
.kpis .l { font-size: 7.8pt; color: #5b6b7c; }
.shot { width: 100%; border: .8px solid #c3d3e4; margin: 1.6mm 0 1mm 0; }
.two { display: flex; gap: 3mm; align-items: flex-start; }
.two > div { flex: 1 1 0; }
.note { background: #f7f9fc; border-left: 3px solid #1b5e9c; padding: 1.8mm 2.5mm; font-size: 8.8pt; margin-top: 2mm; }
table { border-collapse: collapse; width: 100%; font-size: 9.2pt; margin: 1.5mm 0; }
th { background: #eef3f9; text-align: left; padding: 1.4mm 2mm; border-bottom: 1.1px solid #c3d3e4; }
td { padding: 1.3mm 2mm; border-bottom: .8px solid #e3e9f0; vertical-align: top; }
"""


def build() -> Path:
    r = json.loads((OUT / "spss_results.json").read_text(encoding="utf-8"))
    m, rg, ch = r["metrics"], r["regression"], r["chisq"]
    ci = r["nps_ci"]
    dest = ROOT / "portfolio"
    dest.mkdir(exist_ok=True)

    html = f"""<!doctype html><html><head><meta charset="utf-8">
<title>Applied analytics portfolio — Un Chi Kit</title><style>{CSS}</style></head><body>

<h1>Applied analytics &amp; data systems — portfolio summary</h1>
<div class="sub"><b>Un Chi Kit</b> · Macau SAR · +853 6318 3022 · unchikit123@gmail.com</div>
<div class="sub">MSc in Data Science (Artificial Intelligence Application), University of Macau · BSc Civil Engineering ·
2nd place, Macau SAR selection for the 46th WorldSkills Competition (Business Software Solutions)</div>

<div class="kpis">
  <div><div class="v">23,162</div><div class="l">service contacts modelled</div></div>
  <div><div class="v">36</div><div class="l">DAX measures</div></div>
  <div><div class="v">30</div><div class="l">automated data-quality checks</div></div>
  <div><div class="v">{m['nps_points']:+.1f}</div><div class="l">NPS (bootstrap 95% CI {ci[0]:+.1f}–{ci[1]:+.1f})</div></div>
</div>

<h2>1 · Customer-service operations dashboard — Power BI, SQL, Python</h2>
<div class="two">
  <div>
    <ul>
      <li>Designed a <b>star-schema model</b> over 23,162 contacts and 15,721 cases (26 weeks, five channels),
          with a date table and six dimensions.</li>
      <li>Authored <b>36 DAX measures</b> covering SLA attainment, first-contact resolution, handle time,
          backlog ageing, CSAT/CES/NPS and cost per contact — each definition documented with its pitfalls.</li>
      <li>Added <b>30 automated data-quality checks</b> (key integrity, Likert ranges, flag coherence, calendar
          coverage) that gate a refresh instead of silently publishing wrong numbers.</li>
      <li>Every figure is validated against an <b>independent pandas implementation</b>, so the dashboard
          numbers are provably reproducible.</li>
    </ul>
    <table>
      <tr><th>Finding</th><th>Evidence</th></tr>
      <tr><td>Phone wait time doubled from week 14</td>
          <td>CES 5.09 → 3.98 (−1.11, p &lt; .001); CSAT 4.18 → 3.37</td></tr>
      <tr><td>Email first-response SLA collapsed from week 23</td>
          <td>80.6% → 23.9% (p ≈ 1e-296); open backlog concentrated in 7–30 day bucket</td></tr>
      <tr><td>Volume spike was <i>not</i> an experience problem</td>
          <td>Billing contacts 153 → 302/week with CSAT flat (4.01 vs 4.11)</td></tr>
    </table>
  </div>
  <div>{img(OUT / "screens" / "mvp-service-operations.png", "shot")}</div>
</div>

<h2>2 · Customer-experience metrics &amp; statistical analysis — SPSS, Python</h2>
<div class="two">
  <div>
    <ul>
      <li>Built an <b>SPSS-native dataset</b> (.sav with variable labels, value labels and measurement levels)
          plus full <b>SPSS syntax</b> for NPS/CES/CSAT, bootstrap confidence intervals, chi-square,
          Welch t-tests, ANOVA with Tukey post-hoc, Kruskal-Wallis, standardised-beta driver analysis and
          ordinal logistic regression (PLUM).</li>
      <li><b>NPS {m['nps_points']:+.1f}</b> ({m['promoter']:.1%} promoters, {m['detractor']:.1%} detractors),
          bootstrap 95% CI [{ci[0]:+.1f}, {ci[1]:+.1f}] — resampled because NPS is a difference of proportions.</li>
      <li><b>First-contact resolution is the dominant driver of CSAT</b> (standardised β = {rg['betas']['first_contact_resolution']:+.2f},
          R² = {rg['r2']:.3f}), ahead of escalation (−0.24), transfers (−0.11) and wait time (−0.04).</li>
      <li>Channel and NPS group are <b>not independent</b> (χ² = {ch['chi2']:.1f}, df {ch['dof']}, p &lt; .001,
          Cramér's V = {ch['cramers_v']:.3f}).</li>
      <li><b>Methodological control:</b> pooling wait time across channels suggests longer waits raise FCR
          (+0.39, p &lt; .001); tested within channel the effect disappears and reverses for live chat
          (−0.12, p = .002) — a channel confound that would have produced the wrong recommendation.</li>
    </ul>
    <div class="note">Deliverables: 4-page bilingual findings report, SPSS <code>.sav</code> + <code>.sps</code>,
      and a procedure-by-procedure SPSS ⇄ Python equivalence table. No SPSS licence was available on this
      machine, so the syntax is shipped with expected values and cross-checked numerically in Python —
      stated openly rather than faked.</div>
  </div>
  <div>{img(OUT / "04_queue_satisfaction.png", "shot")}</div>
</div>

<h2>How this maps to the role</h2>
<table>
  <tr><th>Requirement</th><th>Evidence in this portfolio</th></tr>
  <tr><td>Develop and maintain databases and data systems</td>
      <td>Star schema (7 tables), SQL data-quality gates, reproducible pipeline</td></tr>
  <tr><td>Automate workflows for real-time analytics and performance tracking</td>
      <td>Automated model/report generation from source files; 30 checks that block a bad refresh</td></tr>
  <tr><td>Statistical tools for diagnosis and prediction</td>
      <td>Bootstrap CIs, chi-square, Welch t-tests, ANOVA + Tukey, Kruskal-Wallis, regression, ordinal logistic</td></tr>
  <tr><td>NPS, CES and satisfaction surveys</td>
      <td>Full metric definitions, response-rate and non-response handling, driver analysis</td></tr>
  <tr><td>Power BI, SPSS, Python, SQL, Excel/VBA</td>
      <td>Used throughout; measure definitions, SPSS syntax and .sav files all included</td></tr>
</table>

<div class="note"><b>Disclosure.</b> All data is synthetic, generated by a seeded, documented generator;
the projects demonstrate method and tooling, not any organisation's real performance. Every reported
figure is reproducible by running the included scripts. Code, documentation and outputs are available
on request or in a repository.</div>

</body></html>"""

    out_path = dest / "Portfolio_Summary_UnChiKit.html"
    out_path.write_text(html, encoding="utf-8")
    return out_path


if __name__ == "__main__":
    print("wrote", build())
