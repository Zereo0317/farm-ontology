# Seges — 把農地的真值變成可金融化的信任資產

> **2026-11-22 evidence hold:** Financial-return, trading-readiness, legal-exemption, first-in-the-world, and farmer-outcome claims in this historical overview are unverified. Do not use them for investment solicitation, operational decisions, or external representations until independently reviewed. The T3-R report contains inconsistent provenance and a suspected price-unit error.


> 專案完整介紹（2026-11-20 版）· repo：`Zereo0317/farm-ontology` · 官網：<https://seges.ai>

---

## 一句話

**Seges 是世界上第一個用 hash-chained「出生證明」記錄農業數據的決策系統**——衛星預測作物、田間實測驗證、授權內建、金融對沖——從北海道一塊 0.4 公頃的大豆田真實上路。

---

## 1. 為什麼存在（Hook）

> **A farming automation solution that makes food production benefit everyone.** — Zereo

兩個真問題：

1. **勞力**：已開發國家的農田人力大多短缺——自動化不是選項，是必然。
2. **主權**：國家自產食物是國安問題——進口比例越高，談判桌越小。

三個答案（我們的解方）：

1. **可靠自動化**：可靠且能自我演化的農田自動化基礎設施——感測器盯著、閥門聽紀錄的，每一次修正都被學住。
2. **風險對沖**：機器把田做壞了，你還是站得住一個倉位——損失不是你唯一的結局。
3. **地主被動收入**：每個月進帳薪資。原來種田的時間，拿來度假與陪伴家人。

而資金端的故事：把錢投進來，我們用**資訊領先優勢**做金融套利；**15–35% 的利潤撥給飢荒、永續與環保，其餘回到投資者口袋**。

---

## 2. 這個系統的獨特信仰（Charter，四條，tests 強制）

1. **Stdlib-only Python**——執行期零第三方依賴；web 端也 dependency-light。
2. **Fail closed**——缺輸入、過期授權、不明註冊 ⇒ 拒絕**並記錄**；缺口被公告，永不被猜測掩蓋。
3. **No invented numbers**——每個數值必須攜帶：原生空間解析度、生效時間、發行者、授權、誤差標記。任何一個缺 ⇒ 數值不存在。
4. **Consent-first**——農場級數據流向任何市場面產物都需要農夫書面 grant；Class C（結算/避險/觸發/自然單位）全面封閉待人類批准。

**「拒絕比我們承諾的多，是刻意的」**——10 公里的格網值永遠不冒充田塊量測；join 永不改寫支援；過期授權自動降級；未知就誠實寫 `unknown`。

---

## 3. 護城河：三層資訊優勢（誰都拿不走的原因）

| 優勢 | 機制 | 為何持續 |
|---|---|---|
| **時間領先** | 多訊號匯流即記錄：災害 watcher + Sentinel-2/VHI + WASDE 週期 | 記錄從「官方發布瞬間」開始，不等交易員讀到新聞 |
| **粒度** | 田塊/感測器真值 vs 公開縣級統計 | 帳本保留**原生支援**——分得清「這塊田真的受損」vs「5 公里格子說受損」 |
| **可證明性** | `factsAt` 點時查詢 + hash-chained ledger | 審計員可重放任意歷史時點的「我們當時知道什麼」——競爭者筆記本做不到 |

---

## 4. 系統實況（2026-11-20，全部 live）

| 面向 | 地址 / 備註 |
|---|---|
| **官網（六語：繁/简/EN/日/泰/阿）** | <https://seges.ai>（Cloudflare worker → 五語 landing，min-instances=1） |
| **田間工作台** | <https://seges.ai/farm>（通行碼閘後： advisories + scene thumbs） |
| **手機釘界 /walk** | 站田角按一下→GPS+精度逐角 verbatim→governed polygon+鞋帶面積估算（免 token） |
| **真實報告 /report/biratori-1119** | 24h JMA MSM 捕捉、五農區成熟度驗證 ±15%、投資人 ROI/風險分頁（公開） |
| **Pitch 頁** | /pitch/architecture·data·fieldday·reliable（六語） |
| **Decision API** | /farm·/farm/weather·/planet·/ee·/licences·/ingest-status·/leads |
| **數據帳本** | GCS `farm-seges-ai-records`（versioned；obs/boundary/leads/notes） |
| **TVLI 計劃管道** | 5 × Cloud Scheduler；ingest workers（weather/planet/ndvi/hazard/nightly-export） |
| **授權引擎** | 操作者 grant 已執行：6/11 feeds settlement=OK；specimen 永不解鎖；fail-closed |
| **測試** | **1744 tests OK**（14 opt-in skips），hermetic，CI 綠燈才上 staging |

---

## 5. 數據現況（真實，帳本上有身份的）

- **62 筆土壤化學**（2023–2026，Tomiyasu Airtable DOM 收割）：pH/EC/CEC/NPK/微量元、四年四區
  → 施肥引擎逐一開口：41 塊缺 N+OM、5 塊缺 OM、16 塊 2023 被誠實拒（3 年 staleness 規則）
- **Hiroki Tomiyasu 田**（Biratori 42.7018, 142.4071）— pin 已有；BoundaryVersion 待明天田野日 v1
- **24h JMA MSM weather capture**（11-19，fixtures/live）
- **Planet trial 至 2026-12-17**（11-30 決定是否購買）；Sentinel-2 備援路線已寫
- **明日田野日**：綠蔥田（收穫目標：傳票+瓶數+四角）+ 大豆田（真值：實際收穫日/重量 vs 預測 R8=9/27，±7 天命中判定）

---

## 6. 金融套利（doctrine × 程式碼 × 誠實數學）

**方法**（`docs/alpha-fairness-doctrine.md` §1–8；編碼進 `markets/rails.py`）：

| 訊號狀態 | 自營帳 | 對農夫 |
|---|---|---|
| 確定減產 | 買 put/做空期貨，size 對齊實體量 | 止損決策支援＋**披露自身避險**（CI 強制條款） |
| 確定增產 | 遠期實體採購鎖價 | 投入品融資、收益分享 |
| 50/50 | 只做波動率（cost-capped straddle/collar） | 只給機率圖；**不賣任何東西** |
| 災害臨近 | 公眾恐慌前合法減倉（反操縱界線內） | 觸發緊急 SOP——農夫保護 > 帳本利潤 |

**五條公平軌**（CI enforce）：同時部位揭示 / 上行分享 / 「農夫看到避險單還會簽嗎？」ticket-測試 / 同意優先 / 真實性門（缺授權即 fail-closed）。

**合法邊界**（香港實體）：自營免 CFTC/SFC 執照；代客/收費建議=執照需求（產品已繞開）；公開數據合成**非內線**；美國預發布窗口=CFTC Rule 180.1——我們不在圈内也永遠不碰。

**誠實數學**：T3-R 真實 ZS=F 2021-2025 回測 **+0.7%/季 edge、3W/2L**；1,000 ha 聚合 ≈ $9,600/季；10,000 ha ≈ $96,000/季；edge 提升至 3%（per-season breakout 重推）可 ×4。災害事件 put 可 +5–15%／-100%，靠組合管理。

---

## 7. 全球擴張地圖（作物 ↔ 期貨 ↔ 開放度）

| 區域 | 作物 | 期貨機會 | 外資易進度 |
|---|---|---|---|
| 日本（現在） | 大豆/米/蔥 | CBOT ZS 對沖 | ✅ 本場 |
| 東南亞 | 棕櫚油/稻/糖 | **FCPO**、ICE SB | ✅ 最佳入口 |
| 非洲 | 可可/咖啡/白玉米 | ICE CC·KC、SAFEX | ✅ 商品自由 |
| 中國 | 玉米/豬/粕 | DCE/ZCE | ⚠️ QFII 摩擦 |
| 印度/南亞 | 稻/小麥/棉 | NCDEX（外资受限） | ⚠️ SaaS-only |
| 中亞 | 小麥（哈薩克） | 靠 CBOT ZW 對沖 | ✅ |

**地面設施（護城河所在）**：純衛星模式=零護城河零真值，必死。效率解：合作社級微型氣象站（$300）+ 代表田土壤水分探針（$500-2,000）+ 農夫手機回報（$0）——**每農場邊際成本 $5–20/年**，透過合作社/JA 進入（不一一找農夫）。

---

## 8. 投資人 Pitch 路線（三段驗證）

```
Phase 1（現在做，0 成本）— 預測力證明
  Hokkaido 5–50 farms, R8 預測 ±7天 命中率 >70%
  KPI: farms / ha / hit-rate

Phase 2（2027）— 金錢證明
  1,000+ ha 聚合，分期銷售+災害避險 overlay 跑一整年，公開 P&L
  KPI: hedge P&L per ha / drawdown / Sharpe

Phase 3（2028+）— 擴張證明
  棕櫚油（SEA）+ 可可（西非）同構複製，合作社渠道
  Model: SaaS $20–50/farm/yr + 績效費 10–20%
```

**知名同業者對照**：Indigo Agriculture（碳權/市場媒合，曾估值 $69 億）、FBN（直購+數據定價）、Bushel（倉儲物流數據）——**都在同空間但不做 hash-chain 出生證明帳本**。潛在合作：World Bank AgriConnect（2030 觸及 3 億農夫）、JA 全農、CME Group 數據合作、Yanmar/Kubota 感測器佈點。

---

## 9. 還沒解決的事（誠實，human cards + 技術缺口）

### Human cards（非技術、等人）
1. 感測器籃 A（¥112,458）vs B（技適済 ¥126,336）
2. Planet 購買 vs lapse（**11-30 決定**，trial 到 12-17；lapse 路線=Sentinel-2）
3. **公司設立**（香港方向已定）——擋所有第三方簽約
4. Kill-switch contract 簽署（Phase-4 gate）

### 技術缺口（下一個 sprint 可開工）
- T3 per-season breakout re-derivation（+0.7% → 3% 的那一刀）
- 蔥/其他作物 phenology profiles（對照 CO_341）
- 土壤 41+5 塊的 N/OM 補測排程
- 實體執行通道（broker API → trade ledger）
- landing 的 EN/TH/AR 校稿、og:image 六語變體、PDF 產線產品化

---

## 10. 給讀者（新 agent / 合作方 / 投資人）的三個入口

- **看成果**：<https://seges.ai> → /report/biratori-1119
- **讀骨法**：`docs/alpha-fairness-doctrine.md`（8 章，公平軌的全部思想）
- **驗能力**：`python -m unittest discover -s tests -t .`（1744 tests，hermetic）

**聯繫**：Zereo0317（founder；gcloud `segescloud`；Cloudflare zone：Hyuchen869 之下）

> *「拒絕比承諾多、記錄比記得的長、同意先於使用」——這就是 Seges 的樣子。*
