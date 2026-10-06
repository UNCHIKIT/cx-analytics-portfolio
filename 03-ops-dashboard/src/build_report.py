"""Build the bilingual (繁中 / English) findings report for portfolio piece A.

Reads outputs/spss_results.json + the analysis charts, writes a self-contained
outputs/findings.html (images inlined as base64), which is then printed to
outputs/findings.pdf by Chromium.

Run:  python src/build_report.py
"""

from __future__ import annotations

import base64
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"

CSS = """
@page { size: A4; margin: 14mm 13mm; }
* { box-sizing: border-box; }
body { font-family: "Microsoft JhengHei", "Segoe UI", sans-serif; color: #1b2430;
       font-size: 10.5pt; line-height: 1.5; margin: 0; }
h1 { font-size: 17pt; margin: 0 0 2mm 0; }
h2 { font-size: 12.5pt; margin: 6mm 0 2mm 0; padding-bottom: 1mm;
     border-bottom: 1.5px solid #1b5e9c; color: #12456f; }
h3 { font-size: 11pt; margin: 4mm 0 1.5mm 0; color: #12456f; }
.sub { color: #5b6b7c; font-size: 9.5pt; margin-bottom: 4mm; }
table { border-collapse: collapse; width: 100%; margin: 2mm 0 3mm 0; font-size: 9.5pt; }
th { background: #eef3f9; text-align: left; padding: 1.6mm 2mm; border-bottom: 1.2px solid #c3d3e4; }
td { padding: 1.4mm 2mm; border-bottom: 0.8px solid #e3e9f0; vertical-align: top; }
.kpi { display: flex; gap: 3mm; flex-wrap: wrap; margin: 3mm 0; }
.kpi div { flex: 1 1 28%; border: 1px solid #c3d3e4; border-radius: 3px; padding: 2mm 2.5mm; }
.kpi .v { font-size: 14pt; font-weight: 700; color: #12456f; }
.kpi .l { font-size: 8.5pt; color: #5b6b7c; }
ul { margin: 1mm 0 2mm 5mm; padding: 0; }
li { margin-bottom: 1.2mm; }
.note { background: #f7f9fc; border-left: 3px solid #1b5e9c; padding: 2mm 3mm; font-size: 9pt; }
.charts { display: flex; gap: 3mm; flex-wrap: wrap; }
.charts img { width: 49%; border: 0.8px solid #e3e9f0; }
.pagebreak { page-break-before: always; }
.en { color: #33475b; font-size: 9.5pt; }
"""


def img(name: str) -> str:
    path = OUT / name
    if not path.exists():
        return ""
    b64 = base64.b64encode(path.read_bytes()).decode("ascii")
    return f'<img src="data:image/png;base64,{b64}" alt="{name}">'


def build() -> str:
    r = json.loads((OUT / "spss_results.json").read_text(encoding="utf-8"))
    m, rg, an, ch = r["metrics"], r["regression"], r["anova"], r["chisq"]
    ci = r["nps_ci"]
    betas = rg["betas"]
    top_driver = max(betas, key=lambda k: abs(betas[k]))
    nicename = {"first_contact_resolution": "首次聯絡解決 FCR", "escalated": "升級 escalated",
                "transfer_count": "轉接次數 transfers", "log_wait": "等候時間（對數）log wait"}

    tests_zh = [
        ("NPS 淨推薦值", f"{m['nps_points']:+.1f}",
         f"2,000 次 bootstrap 95% CI [{ci[0]:+.1f}, {ci[1]:+.1f}] — 不算寬，可作為季度 KPI"),
        ("CSAT top-box（4–5 分）", f"{m['csat_top_box']:.1%}", f"平均 {m['csat_mean']:.2f}／5；top-box 才是標準報法"),
        ("CES % easy（5–7 分）", f"{m['ces_easy']:.1%}", f"平均 {m['ces_mean']:.2f}／7"),
        ("渠道 × NPS 分組獨立性", f"χ² = {ch['chi2']:.1f}（df {ch['dof']}）",
         f"p &lt; .001，Cramér's V = {ch['cramers_v']:.3f} — 渠道與推薦意願有關聯，電話偏向貶損者"),
        ("服務線 CSAT 差異", f"F = {an['f']:.1f}",
         f"p &lt; .001；Levene p &lt; .001（變異數不等）→ 以 Welch F = 71.7、Kruskal-Wallis H = 271.0 為準"),
        ("CSAT 驅動因子（標準化 Beta）", f"{top_driver}  {betas[top_driver]:+.2f}",
         "回歸 R² = " + f"{rg['r2']:.3f}" + "；升級 −0.24、轉接 −0.11、等候 −0.04"),
    ]

    html = f"""<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8"><title>CX 指標引擎 — 統計分析報告</title>
<style>{CSS}</style></head><body>

<h1>作品 A · CX 指標引擎 — 客戶問卷統計分析</h1>
<div class="sub">Portfolio piece A · CX metrics engine — survey statistics ·
資料：4,256 份回覆後問卷（26 週、5 渠道、5 服務線）· 檔案：<code>data/cx_survey.sav</code> ·
語法：<code>analysis/cx_metrics.sps</code> · 對照實作：<code>src/spss_equivalent.py</code></div>

<div class="kpi">
  <div><div class="v">{m['nps_points']:+.1f}</div><div class="l">NPS（95% CI {ci[0]:+.1f} ~ {ci[1]:+.1f}）</div></div>
  <div><div class="v">{m['csat_top_box']:.1%}</div><div class="l">CSAT top-box</div></div>
  <div><div class="v">{m['ces_easy']:.1%}</div><div class="l">CES % easy</div></div>
  <div><div class="v">{betas['first_contact_resolution']:+.2f}</div><div class="l">FCR 標準化 Beta（最強驅動）</div></div>
</div>

<h2>一、核心發現</h2>
<ul>
  <li><b>NPS = {m['nps_points']:+.1f}</b>（推薦者 {m['promoter']:.1%}、貶損者 {m['detractor']:.1%}），95% 信賴區間
      [{ci[0]:+.1f}, {ci[1]:+.1f}]。以 bootstrap 取得信賴區間，是因為 NPS 是兩個比例之差，不是平均數。</li>
  <li><b>真正驅動 CSAT 的是「一次解決」</b>：FCR 標準化 Beta = {betas['first_contact_resolution']:+.2f}（p &lt; .001），
      遠大於等候時間（{betas['log_wait']:+.2f}）。<b>升級（escalation）是最負面的因子</b>（{betas['escalated']:+.2f}），
      轉接次數亦為負（{betas['transfer_count']:+.2f}）。</li>
  <li><b>投訴與升級服務線是唯一明顯落後的隊列</b>：CSAT 3.29，比其他隊列低 0.68–0.93 分
      （Tukey HSD，10 組中有 8 組顯著差異）。</li>
  <li><b>渠道與推薦意願並非獨立</b>：χ² = {ch['chi2']:.1f}（df {ch['dof']}，p &lt; .001，Cramér's V = {ch['cramers_v']:.3f}）。
      電話的貶損者比例明顯偏高（780/1,973）。</li>
  <li><b>方法上的重點：等候時間的合併檢定是假象。</b>合併測試顯示「等候越久、FCR 越高」（+0.39, p &lt; .001），
      但這是渠道混淆 —— 非同步渠道（電郵、表格）「等候」以小時計且 FCR 本來就高。
      <b>分渠道檢定後效果消失或反轉</b>（線上對話：−0.12, p = .002）。</li>
  <li>CSAT 為有序尺度，故以 <b>ordinal logistic（PLUM）</b> 驗證：FCR +2.22、升級 −1.55、轉接 −0.36、等候 −0.05，
      方向與一般回歸一致，結論穩健。</li>
</ul>

<h2>二、統計檢定總表</h2>
<table>
  <tr><th>檢定 / Metric</th><th>結果 / Result</th><th>解讀 / Reading</th></tr>
  {"".join(f"<tr><td>{a}</td><td><b>{b}</b></td><td>{c}</td></tr>" for a, b, c in tests_zh)}
</table>

<h2>三、建議行動</h2>
<ul>
  <li><b>把「一次解決率」當成第一 KPI</b>（Beta {betas['first_contact_resolution']:+.2f}），而非只盯 NPS。
      NPS 是落後指標，FCR 是可控的領先指標。</li>
  <li><b>投訴與升級隊列單獨治理</b>：CSAT 3.29、FCR 最低，且升級本身是最大負向因子。先把「升級原因」分類，再設目標。</li>
  <li><b>電話渠道</b>的貶損者比例偏高 → 對應前面作品 03 的電話人手缺口，兩份分析互相印證。</li>
  <li><b>報表紀律</b>：每次都報「回覆率 + 信賴區間」。本次回覆率僅約 27%，無回應偏誤必須揭露。</li>
</ul>

<div class="note"><b>工具說明：</b>本機無 SPSS 授權，故 <code>cx_metrics.sps</code> 未在 SPSS 執行；
同樣的統計量以 Python（scipy / statsmodels）獨立實作於 <code>src/spss_equivalent.py</code>，
逐項對照表見 <code>outputs/spss_equivalence.md</code>。在 SPSS 或 PSPP 執行該語法應得到相同數字
（<code>BOOTSTRAP</code> 與 <code>PLUM</code> 需 SPSS；PSPP 不支援）。</div>

<div class="pagebreak"></div>
<h1>Portfolio piece A — CX Metrics Engine (English)</h1>
<div class="sub">4,256 post-contact survey responses · 26 weeks · 5 channels · 5 service queues ·
synthetic data (<code>src/generate_data.py</code>), SPSS file <code>data/cx_survey.sav</code></div>

<h2>Findings</h2>
<ul>
  <li><b>NPS {m['nps_points']:+.1f}</b> ({m['promoter']:.1%} promoters, {m['detractor']:.1%} detractors),
      bootstrap 95% CI [{ci[0]:+.1f}, {ci[1]:+.1f}]. NPS is a difference of two proportions, so it is
      resampled rather than treated as a mean.</li>
  <li><b>First-contact resolution is the dominant driver of CSAT</b> (standardised Beta
      {betas['first_contact_resolution']:+.2f}, p &lt; .001) — far ahead of wait time
      ({betas['log_wait']:+.2f}). Escalation is the largest negative factor ({betas['escalated']:+.2f}),
      followed by transfers ({betas['transfer_count']:+.2f}). Model R² = {rg['r2']:.3f}.</li>
  <li><b>Complaints &amp; Escalations is the outlier queue</b> (CSAT 3.29 vs 4.01–4.22 elsewhere);
      8 of 10 Tukey HSD pairs differ at p &lt; .05.</li>
  <li><b>Channel and NPS group are not independent</b>: χ² = {ch['chi2']:.1f}, df {ch['dof']}, p &lt; .001,
      Cramér's V = {ch['cramers_v']:.3f}; Phone carries the highest detractor share.</li>
  <li><b>Methodological point:</b> pooling wait time across channels produces a spurious positive
      association with FCR (+0.39, p &lt; .001) because asynchronous channels have hour-scale
      "waits" and higher resolution rates. Tested within channel, the effect disappears or reverses
      (Live Chat: −0.12, p = .002).</li>
  <li>Because CSAT is ordinal, an ordinal logistic model (SPSS <code>PLUM</code>) was run as a
      robustness check: FCR +2.22, escalation −1.55, transfers −0.36, log-wait −0.05 — same directions.</li>
</ul>

<h2>Method notes</h2>
<ul>
  <li>Welch t-tests throughout (unequal variances); Levene p &lt; .001 for CSAT by queue, hence the
      Welch ANOVA and Kruskal-Wallis results are reported alongside the classic F.</li>
  <li>Standardised betas come from regressing z-scored CSAT on z-scored predictors, which is what
      SPSS reports in the <i>Beta</i> column.</li>
  <li>The proportional-odds (parallel lines) test is produced by SPSS <code>PLUM /PRINT=TPARALLEL</code>;
      the Python reference cannot reproduce that specific test — stated rather than glossed over.</li>
</ul>

<h2>Limitations</h2>
<ul>
  <li>Data is <b>synthetic</b>: the numbers validate the method, not any real organisation.</li>
  <li>Response rate ≈ 27% on closed cases; non-response bias is material and unquantified.</li>
  <li>FCR is a proxy (no follow-up contact within 7 days), not a verified resolution.</li>
  <li>Regression coefficients are associations: the causal claim for FCR would need an experiment
      (e.g. routing change) or a natural experiment.</li>
</ul>

<h2>Charts</h2>
<div class="charts">{img('02_satisfaction_trend.png')}{img('04_queue_satisfaction.png')}
{img('01_volume_vs_sla.png')}{img('03_backlog_aging.png')}</div>

</body></html>"""
    (OUT / "findings.html").write_text(html, encoding="utf-8")
    return str(OUT / "findings.html")


if __name__ == "__main__":
    print("wrote", build())
