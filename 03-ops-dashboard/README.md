# 作品 03 · 客服營運即時儀表板 (Customer Service Operations Dashboard)

**一句話 / One line.** 26 週、23,162 通客戶聯絡的五渠道客服資料，建成 star schema 並定義全套營運與
體驗指標，找出兩個真正的服務問題（電話人手缺口、Email 積壓），並排除一個假警報（宣傳活動帶來的
聯絡量上升）。
*26 weeks and 23,162 customer contacts across five channels, modelled as a star schema with a full
service-and-experience metric layer — surfacing two real problems (a phone staffing gap and an email
backlog) while ruling out one false alarm (a campaign volume spike with no satisfaction impact).*

---

## 30 秒摘要 / 30-second summary

- 我建立了**聯絡（contact）粒度**的 fact table，並以**個案（case）**為單位定義 FCR 與重複聯絡率 —
  大部分客服儀表板把個案指標算在聯絡粒度上，這是錯的。
  量測層分成五組：服務量、速度與 SLA、解決品質、體驗（CSAT/CES/NPS）、成本與積壓。
- **第一個發現：** 第 14 週起電話平均等候由 **49 秒升至 100 秒**，電話 CES 由 **5.09 跌至 3.98**
  （差異 −1.11，95% CI ±0.11，p < 0.001），CSAT 由 **4.18 跌至 3.37**（p < 0.001）。
- **第二個發現：** 第 23 週起 Email 首次回覆 SLA 由 **80.6% 崩至 23.9%**（p ≈ 1e-296），
  未結案聯絡由 29/4,843 升至 253/1,079 — 積壓沒有被消化，帳齡集中在 Email 的 7–30 天區間。
- **排除假警報：** 第 18–19 週帳務（Billing）個案量由每週 153 升至 302（宣傳活動），
  但 CSAT 維持 4.01 vs 4.11（差異 −0.10）。**量大 ≠ 體驗有問題**，不應優先處理。
- **最差隊列：** 投訴與升級 CSAT 3.29 / NPS −35，明顯低於其他隊列（+10 至 +27）。

## 儀表板頁面 / Report pages

| 頁面 | 內容 | 主要指標 |
|---|---|---|
| 1. 服務營運 | 量、SLA、隊列×渠道矩陣 | Contacts, SLA %, FCR %, AHT, Abandonment %, Cost per contact |
| 2. 客戶體驗 | 滿意度趨勢與驅動因素 | CSAT top-box %, CES % easy, NPS, Response rate % |
| 3. 積壓與帳齡 | 未結案與帳齡分佈、可下鑽 | Open backlog, Oldest open days, >7 days |

## 核心指標 / Headline KPIs（實測值，非示例）

| 指標 | 值 |
|---|---|
| Contacts / Cases | 23,162 / 15,721（每案 1.47 通） |
| Answered / Abandonment | 22,193 / 4.2% |
| SLA attainment | 58.7% |
| ASA（即時渠道）/ 首次回覆（非同步） | 73 秒 / 4.3 小時 |
| AHT | 336 秒（5.6 分鐘） |
| FCR / 重複聯絡率 / 升級率 | 62.0% / 32.1% / 11.6% |
| 問卷回覆率 | 27.1%（15,721 個已結案個案中 4,256 份回覆） |
| CSAT top-box / CSAT 平均 | 71.2% / 3.99（5 分制） |
| CES 平均 / % 容易 | 4.84（7 分制）/ 61.3% |
| NPS | +11.6（推薦者 41.7%、貶損者 30.1%） |
| 每次聯絡成本 / 六個月總成本 | MOP 13.14 / MOP 304,462 |
| 未結案積壓 / 最舊天數 | 431 通 / 46 天 |

## 作品 A：統計分析層 / Statistics layer（同一資料集，JD 的 SPSS 要求）

| 檔案 | 內容 |
|---|---|
| `data/cx_survey.sav` | SPSS 原生資料檔：4,256 份回覆 × 26 變數，含變數標籤、數值標籤、measure level |
| `analysis/cx_metrics.sps` | 完整 SPSS 語法：NPS/CES/CSAT 定義、bootstrap CI、卡方、t 檢定、ANOVA + Tukey、Kruskal-Wallis、標準化 Beta 回歸、PLUM 有序回歸（每段都附**預期數值**註解，方便驗收） |
| `src/make_sav.py` | 產生 `.sav` 並讀回驗證 |
| `src/spss_equivalent.py` | 同一批統計量的 Python 實作（scipy / statsmodels），直接讀 `.sav` |
| `outputs/spss_equivalence.md` | SPSS 程序 ⇄ Python 對照表（逐項數字） |
| `outputs/findings.pdf` / `.html` | 中英雙語 4 頁發現報告（繁中 2 頁 + English 1 頁 + 圖表 1 頁） |
| `outputs/screens/findings-page1.png` | 報告首頁截圖（供投遞預覽） |

**核心統計發現：**

- **NPS +11.6**（推薦者 41.7%、貶損者 30.1%），bootstrap 95% CI [+9.1, +14.0]（2,000 次重抽樣；NPS 是兩個比例之差，故用重抽樣而非平均數的信賴區間）
- **CSAT 的最強驅動因子是「首次聯絡解決」（標準化 Beta +0.49, p<.001）**，遠大於等候時間（−0.04）；升級為最大負向因子（−0.24），轉接亦為負（−0.11）；R² = 0.347
- **投訴與升級服務線是唯一落後隊列**（CSAT 3.29，低 0.68–0.93 分；Tukey HSD 10 組中 8 組顯著）
- **渠道與 NPS 分組不獨立**（χ² = 209.7, df 8, p<.001, Cramér's V = 0.157），電話貶損者比例最高
- **方法重點（渠道混淆）**：合併檢定顯示「等候越久 FCR 越高」（+0.39, p<.001）是**假象** —— 非同步渠道「等候」以小時計且 FCR 本來較高。**分渠道檢定後效果消失或反轉**（線上對話 −0.12, p=.002）。這是本次分析最有價值的判斷。
- **穩健性**：CSAT 為有序尺度，以有序 logistic（SPSS `PLUM`）複核，四個係數方向與一般回歸一致。

**工具誠信聲明**：本機無 SPSS 授權，故 `.sps` 未在 SPSS 執行；同一批數字以 Python 獨立實作並逐項對照（`outputs/spss_equivalence.md`）。在 SPSS 或 PSPP 執行該語法應得到相同結果（`BOOTSTRAP`、`PLUM` 需 SPSS）。

## SPSS 交付策略 / SPSS deliverable strategy

JD 明列 SPSS，但本機沒有 SPSS 授權。處理方式是**誠實且可驗證**的三件交付物，不做假輸出：

| 交付物 | 檔案 | 說明 |
|---|---|---|
| SPSS 原生資料檔 | `data/cx_survey.sav` | 由 `src/make_sav.py` 產生（`pyreadstat`）：4,256 筆回覆 × 24 個變數，**含變數標籤、數值標籤、measure level**（`csat`/`ces`/`nps` 為 ordinal、`channel`/`queue` 為 nominal、`wait_seconds` 為 scale）。SPSS / PSPP / JASP / jamovi 可直接開啟 |
| SPSS 語法 | `analysis/*.sps` | 所有統計檢定的 SPSS 語法（作品 A 交付） |
| 等價 Python 實作 | `src/kpi_reference.py` | 同一批數字用 scipy/statsmodels/pandas 獨立算出，作為對答案的參考 |

**為什麼這樣做**：`.spv` 輸出檔是 SPSS 專有二進位容器，只有 SPSS 本身能產生。與其假造 `.spv`，不如交付「真實的 `.sav` + 可執行的 `.sps` + 獨立驗證過的數字」，並在 README 註明語法以 PSPP/JASP 執行（若在 UM 取得 SPSS 授權，同一份 `.sps` 可直接在 SPSS 跑出 `.spv`）。

從 `.sav` 讀回後的驗證值（與 `outputs/kpi_reference.md` 一致）：NPS +11.6、CSAT top-box 71.2%、CSAT 平均 3.99、CES % 容易 61.3%、CES 平均 4.84。
注意：此子集只含**有回覆問卷的個案**，故其 FCR 61.3% 與全量個案 62.0% 略有差異 —— 這是無回應偏誤的體現，不是錯誤。

## 驗收記錄 / Verification log（2026-10-05）

在 Power BI Desktop（專案檔 `powerbi/CXOps.pbip`）實測：

| 檢查 | 結果 |
|---|---|
| 語意模型 | `資料表 (8)`、`量值 (36)`、`運算式 (1)`、6 條關聯；由 TMDL 外部寫入後 Power BI 直接接受 |
| 儀表板數值 | Contacts `23 千`、SLA `58.7%`、FCR `62.0%`、AHT `5.6` 分鐘、CSAT top-box `71.2%`、NPS `+12` —— 與 `outputs/kpi_reference.md` 完全一致 |
| 視覺效果 | 6 張卡片 + 週趨勢組合圖 + 隊列 CSAT 條形圖，全部渲染且有資料 |
| 截圖 | `outputs/screens/mvp-service-operations.png` |

**過程中修正的兩個真 bug（都可作為面試素材）：**

1. **`visual.json` 缺 `$schema`** —— PBIR schema 把 `$schema` 列為必填且限定特定版本，漏掉會令視覺**整批被默默丟棄**（不報錯）。修正後才渲染。
2. **DAX 的 BLANK 強制轉換** —— `nps_score <= 6` 在 DAX 中對 BLANK 求值為 `TRUE`（空白被當成 0），把 18,906 筆「未回覆問卷」的聯絡算成貶損者，NPS 顯示 **−433**。三條 NPS 度量值加上 `responded = TRUE()` 過濾後修正為 **+11.6**。
   注意：pandas 參考實作從來沒有這個 bug（NaN 比較為 False）—— 這正是「用參考實作對答案」的價值。

## MVP 範圍 / MVP scope

**先交付 MVP；有面試邀約後才補完整版。** 一件完整交付勝過三件半成品。

| 元素 | MVP（投遞用） | 完整版（後補） |
|---|---|---|
| 資料、DQ 檢查、KPI 定義、pandas 核對 | ✅ 已完成 | ✅ |
| Power BI 報表 | **1 頁**：6 張卡片 + 週趨勢（量柱＋SLA 線）+ 隊列 CSAT 條 | 3 頁、下鑽、scatter、動態標題 |
| 發佈 | Publish 到自己 workspace + 截圖 | 排程重新整理 + on-premises gateway |
| RLS | 略過（口頭講得出來即可） | 角色定義 + View as role |
| 面試防守 | 22 個數字核對 + 3 條限制 | 全套限制與敏感度分析 |

**MVP 完成定義**：一頁報表 + 8 條度量值數字與 `outputs/kpi_reference.md` 完全一致 + 截圖存入
`outputs/screens/` + 不看稿講得出 90 秒故事。到達即停。
逐步操作見 `docs/build-guide.md` 最上方的「MVP path first (30 minutes)」。

**狀態：✅ MVP 已完成**（上面「驗收記錄」有實測證據）。仍未做的只有兩件非必要的事：
① 在 Power BI 按 `Ctrl+S` 把資料寫進快取（這樣下次開啟不用重新整理）；② 發佈到 Power BI 服務取得線上連結（免費 My workspace 即可；分享給他人需 Pro）。

## Context

一個中大型客服中心，五個渠道（電話、電郵、線上對話、社交媒體、網上表格）、五條服務線、
42 名客服、26 週。管理層每月只看人手整理的 Excel 月報，問題往往在事後才被發現。

## Question

1. 服務水準正在哪裡惡化，從哪一週開始？
2. 聯絡量上升是否代表體驗變差？
3. 哪一條服務線最需要優先投入？
4. 滿意度要到什麼程度才值得報警，而不是憑感覺？

## Data

**全部為合成資料**（`src/generate_data.py`，seed 20261005，可完整重現）。客戶投訴敘述、通話逐字稿等
真實個資一律沒有使用。生成器刻意植入五個效果，令分析方法可被驗證：

1. 第 14 週起電話人手缺口 → 等候 ×2.1。
2. 第 23 週起 Email 積壓 → 首次回覆 ×2.5，且未結案不再關閉。
3. 線上對話 FCR（70.1%）明顯高於電話（51.8%）。
4. 第 18–19 週帳務量升（宣傳）而滿意度不變。
5. 投訴與升級隊列滿意度最低。

檔案：`data/fact_interaction.csv`（23,162 列，聯絡粒度）＋ 6 個維度表。

## Method

- **資料模型：** star schema，單一 fact（聯絡粒度）＋ `dim_date`（已標記為日期表）/`dim_channel`/
  `dim_queue`/`dim_agent`/`dim_customer`/`dim_status`。SLA 目標屬渠道屬性（存於 `dim_channel`），
  結果旗標存於 fact — 見 `docs/data-model.md`。
- **指標層：** 所有定義寫在 `docs/metrics-definitions.md`，並以 pandas 實作於
  `src/kpi_reference.py`，Power BI 的 DAX 必須重現同一組數字（`docs/dax-measures.md` 底部有核對表）。
- **統計：** 兩比例 z 檢定（SLA 前後）、Welch t 檢定（CES/CSAT 前後）、Pearson 相關（等候 vs 滿意度，
  並在渠道內做標準化以避免混合尺度）。
- **分開同步與非同步指標：** ASA 只在即時渠道計算，非同步渠道另報首次回覆時間。混算是一個經典錯誤。

## Findings

| # | 發現 | 證據 |
|---|---|---|
| 1 | 電話等候惡化拖累滿意度 | 等候 49→100 秒；CES 5.09→3.98（−1.11，p<0.001）；CSAT 4.18→3.37（p<0.001） |
| 2 | Email 積壓造成 SLA 崩塌 | SLA 80.6%→23.9%（p≈1e-296）；未結案 29/4,843 → 253/1,079；最舊 46 天 |
| 3 | 渠道解決能力差異 | FCR：電郵 70.1%、線上對話 70.1%、網上表格 65.9%、社交 65.3%、電話 51.8% |
| 4 | 假警報 | 帳務量 153→302/週（第 18–19 週），CSAT 4.01 vs 4.11（−0.10，不顯著） |
| 5 | 最差隊列 | 投訴與升級 CSAT 3.29 / NPS −35；其餘隊列 +10 ~ +27 |
| — | 驅動因素 | corr(log 等候, CSAT) = −0.49（即時渠道，渠道內標準化 −0.45）；升級者 CSAT 3.14 vs 非升級 4.10；首次解決 4.26 vs 未解決 3.41 |

## Recommended action

1. **Email 積壓（本週）** — 抽調 2–3 名人力清 7–30 天帳齡，並把「首次回覆 SLA」設為每日盯的指標。
   目標：四週內回到 ≥80%。
2. **電話人手（本月）** — 第 14 週起的等候倍增不是隨機波動（p<0.001），需要重新排班或調整
   桌機分流；以 CES 與 SLA 作領先指標，而非等 NPS 反映。
3. **投訴與升級隊列（本季）** — FCR 只有 57%，先做根因分析（升級原因分類），再談指標目標。
4. **不要做的事** — 不要因第 18–19 週帳務量上升而加人；量與體驗在這次是脫鉤的。
5. **建立起報警線** — 用 4 週滾動的 SLA% 與 CES，而不是單週 NPS（n≈150/週，單週雜訊太大）。

## Impact & limits（必須講的限制）

- 資料是**合成**的：以上數字證明的是**方法**，不是任何真實機構的表現。生成器與植入效果已公開。
- 問卷回覆率 27%，可能存在無回應偏誤（不滿客戶較可能回覆），真實部署時應做加權與無回應分析。
- FCR 以「同一 case 七日內無後續聯絡」定義；真實資料需要客戶層身分串接才能成立。
- 相關不等於因果：等候與滿意度的 −0.49 是關聯；人手缺口的因果解讀需要 A/B 或分段比較。
- 成本為估算單位成本，不是財務實際帳。

## Reproduce

```bash
python src/generate_data.py     # 生成 data/*.csv（seed 固定，可重現）
python src/dq_checks.py         # 30 項資料品質檢查，全部必須 PASS
python src/kpi_reference.py     # 計算全部 KPI + 驗證植入效果，輸出 outputs/
python src/make_sav.py          # 產生 SPSS 原生資料檔 data/cx_survey.sav 並讀回驗證
python src/spss_equivalent.py   # 統計檢定（讀 .sav）→ outputs/spss_equivalence.md
python src/build_report.py      # 產生中英雙語報告 outputs/findings.html
# 報告轉 PDF：以 Chromium 列印 findings.html → outputs/findings.pdf
# SPSS 語法：analysis/cx_metrics.sps（在 SPSS 或 PSPP 開啟執行）
# Power BI：專案檔在 powerbi/CXOps.pbip（已建好，直接開啟即可）
```

## Files

```
03-ops-dashboard/
├─ README.md                     本檔（case study）
├─ data/                         7 個 CSV（合成資料，utf-8-sig）
├─ src/generate_data.py          生成器（植入 5 個效果，有註解）
├─ src/kpi_reference.py          pandas 版 KPI 實作 + 假設檢定 + 圖表
├─ src/dq_checks.py              30 項資料品質檢查（可作為 pipeline 閘門）
├─ src/make_sav.py               產生 SPSS 原生資料檔 cx_survey.sav（含標籤與 measure level）
├─ src/spss_equivalent.py        統計檢定（scipy/statsmodels）— SPSS 語法的對照實作
├─ src/build_report.py           產生中英雙語 findings 報告（HTML → PDF）
├─ analysis/cx_metrics.sps       SPSS 語法（每段附預期數值）
├─ docs/metrics-definitions.md   指標定義、公式、判斷取捨
├─ docs/data-model.md            star schema、關聯、設計決策、DQ 檢查
├─ docs/dax-measures.md          DAX 度量值（可直接貼）＋ 核對表
├─ docs/build-guide.md           Power BI 逐步建立指南（含發佈/排程/RLS）
└─ outputs/                      kpi_reference.md、週/隊列/渠道 CSV、4 張圖
```

## 圖表 / Charts

| 檔案 | 內容 |
|---|---|
| `outputs/01_volume_vs_sla.png` | 量與 SLA 趨勢（第 14 週人手缺口、第 23 週 Email 崩塌） |
| `outputs/02_satisfaction_trend.png` | CSAT / CES / NPS 趨勢與兩個轉折點 |
| `outputs/03_backlog_aging.png` | 未結案帳齡 × 渠道（Email 主導） |
| `outputs/04_queue_satisfaction.png` | 各隊列 CSAT 與 NPS |
