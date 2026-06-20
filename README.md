# ED newsbot 自建套件

一套「**每天自動把急診新論文推到你的 LINE、並存檔，還能在 LINE 打關鍵字回查**」的個人系統。
本套件是**安裝步驟＋教學**，供你或任何人用**自己的帳號**從零建起來。所有 token、ID 都用佔位符 `<...>`，照著換成你自己的即可。

---

## 你用哪個 AI？走哪條路？

**分流關鍵：你願不願意碰程式碼或終端機？**

| 情況 | 走哪條路 | 特色 |
|---|---|---|
| 用 Claude（Pro／Max／Team／Enterprise），**不想碰程式碼或終端機** | **路1：Claude Routines** | 雲端排程、電腦關機照跑、免腳本、免 API key、最省事 |
| 用 Codex 或其他 AI；或願意跑腳本；或想讓程式可控、自己部署 | **路2：腳本 digest.py** | 本機或自己的伺服器執行，需 python3、需可 POST 對外 |
| 想分享給用別種 AI 的同事 | 給他們**路2** | 路2 不綁 Claude 帳號 |

> **已在跑 Routines 版的人，不必改走路2——路2 是為了讓用別種 AI 的人也能跑這套系統。**

---

## 這套系統有三塊

| 塊 | 做什麼 | 跑在哪 | 前提（路1） | 前提（路2） |
|---|---|---|---|---|
| **A 每日日報** | 每天早上抓 PubMed 急診新論文 → 寫繁中臨床重點 → 推到你的 LINE | 路1：Claude Routines（雲端）；路2：本機或自有伺服器 | Claude 任一付費方案＋開啟 Claude Code on the web | python3、可 POST 對外的環境、任一可呼叫 LLM 的方式 |
| **B 論文存檔** | 把每天推的論文，存成一個 `.md` 進你指定的 Google Drive 資料夾 | 由 A 順手做（同一流程多一步） | Google 帳號 | Google 帳號＋（接 C 時）Drive 落點 |
| **C 互動查詢 bot** | 在 LINE 打關鍵字 → 回查「你存過的論文」或「即時查全 PubMed」 | Google Apps Script（GAS）| Google 帳號 | Google 帳號 |

A 推播、B 存檔、C 回查，**三塊共用同一個 LINE 帳號，但程式各自獨立**——任何一塊壞了不會拖垮其他塊。

---

## 你要先準備

1. **一個 LINE Official Account**（在 [LINE Developers](https://developers.line.biz) 開了 Messaging API channel）
   → 發一組 **long-lived channel access token**（在 channel 的 **Messaging API** 分頁發行，別用會過期的短期 token）；
   → 並到 channel 的 **Basic settings** 分頁最下面複製 **Your user ID**（U 開頭 33 字，這就是你本人的 userId，**不是** Channel ID）。
2. **一個 Google 帳號**（Drive 放存檔、跑 GAS）。
3. **（路1 需要）Claude 付費方案**（Pro／Max／Team／Enterprise 任一即可），且帳號已開啟 **Claude Code on the web**——A 的每日 Routine 要用（免費方案不支援 Routines）。
4. **（路2 需要）python3 環境**，且能對外 POST（不被防火牆擋）。詳見 `A-每日日報/路2-用腳本（適用各AI）-設定與執行.md`。
5. （選用）**Node.js ＋ clasp**：C 的 GAS 程式可用網頁編輯器貼，也可用 [clasp](https://github.com/google/clasp) 命令列建／推／更新（兩種建法在 `C-互動查詢bot（GAS）.md` 的 G1 都有寫）。

---

## 安裝順序（照這個走）

### 路1（Claude Routines，最省事）

1. **`A-每日日報/路1-用Claude-Routines（最省事，雲端）.md`** — 建兩個 Drive 資料夾、設 Routine、貼指令、驗收。（裝 A＋B）
2. **`C-互動查詢bot（GAS）.md`** — 把 GAS 程式部署成 webhook、接上 LINE、驗收。（裝 C；C 會去讀 B 存的資料夾）
3. **`附錄-用GAS當webhook的限制.md`** — 照做 C 之前先掃一遍 GAS 的坑，少踩雷。

### 路2（腳本，適用各 AI）

1. **`A-每日日報/路2-用腳本（適用各AI）-設定與執行.md`** — 讀設定說明；複製 `A-每日日報/config.example.env`、填入你的參數；執行 `A-每日日報/digest.py`。（裝 A＋B）
   - 若想了解在各平台自機重現的細節，另可參考 `A-每日日報/路2-自機重現紀錄.md`。
2. **`C-互動查詢bot（GAS）.md`** — 把 GAS 程式部署成 webhook、接上 LINE、驗收。（裝 C）
3. **`附錄-用GAS當webhook的限制.md`** — 照做 C 之前先掃一遍 GAS 的坑，少踩雷。

---

## 檔案導覽

```
ed-newsbot-kit/
├── README.md                                         ← 你正在看的入口（決策表＋導覽）
│
├── A-每日日報/
│   ├── 路1-用Claude-Routines（最省事，雲端）.md       ← 路1：A+B 安裝教學（含可直接貼的 Routine 指令母本）
│   ├── 路2-用腳本（適用各AI）-設定與執行.md           ← 路2：設定說明
│   ├── 路2-用腳本-排程與各平台.md                    ← 路2：在不同作業系統/平台排程的方法
│   ├── 路2-自機重現紀錄.md                           ← 路2：開發者自機重現步驟紀錄（參考）
│   ├── digest.py                                    ← 路2：執行主程式
│   └── config.example.env                           ← 路2：設定範本（複製後填入你的參數）
│
├── C-互動查詢bot（GAS）.md                            ← C 安裝教學（G1–G5）
├── 附錄-用GAS當webhook的限制.md                       ← GAS 當 webhook 的已知限制（建議先讀）
│
└── code/
    ├── Code.gs                                      ← C 的 GAS 程式（全部設定走 Script Properties）
    └── appsscript.json                              ← C 的 web app 設定
```

---

## 安全提醒

- token / userId / webhook 秘密參數，一律放各平台的**設定欄**（Routine 環境變數、GAS Script Properties、`.env` 檔），**不要寫進程式碼、不要外傳**。
- 本套件所有 `<...>` 都是佔位符，請換成你自己的值。
- 互動 bot 用 GAS，有一個安全取捨（沒辦法驗 LINE 簽章），詳見附錄與 `C-互動查詢bot（GAS）.md`。對單人自用可接受；要開放多人請改用正規 serverless。
