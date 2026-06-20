# ED newsbot 自建套件

一套「**每天自動把急診新論文推到你的 LINE、並存檔，還能在 LINE 打關鍵字回查**」的個人系統。
本套件是**安裝步驟＋教學**，供你或任何人用**自己的帳號**從零建起來。所有 token、ID 都用佔位符 `<...>`，照著換成你自己的即可。

---

## 這套系統有三塊

| 塊 | 做什麼 | 跑在哪 | 前提 |
|---|---|---|---|
| **A 每日日報** | 每天早上抓 PubMed 急診新論文 → 寫繁中臨床重點 → 推到你的 LINE | Claude Routines（雲端排程，電腦關機照跑）| Claude 任一付費方案（Pro／Max／Team／Enterprise）＋開啟 Claude Code on the web |
| **B 論文存檔** | 把每天推的論文，存成一個 `.md` 進**你自取名的 Google Drive 資料夾** | 由 A 順手做（同一個 Routine 多一步）| Google 帳號 |
| **C 互動查詢 bot** | 在 LINE 打關鍵字 → 回查「你存過的論文」或「即時查全 PubMed」 | Google Apps Script（GAS）| Google 帳號 |

A 推播、B 存檔、C 回查，**三塊共用同一個 LINE 帳號，但程式各自獨立**——任何一塊壞了不會拖垮其他塊。

---

## 你要先準備

1. **一個 LINE Official Account**（在 [LINE Developers](https://developers.line.biz) 開了 Messaging API channel）
   → 發一組 **long-lived channel access token**（在 channel 的 **Messaging API** 分頁發行，別用會過期的短期 token）；
   → 並到 channel 的 **Basic settings** 分頁最下面複製 **Your user ID**（U 開頭 33 字，這就是你本人的 userId，**不是** Channel ID）。
2. **一個 Google 帳號**（Drive 放存檔、跑 GAS）。
3. **Claude 付費方案**（Pro／Max／Team／Enterprise 任一即可，**不限 Max**），且帳號已開啟 **Claude Code on the web**——A 的每日 Routine 要用（免費方案不支援 Routines）。只想做 C 互動 bot 的話，可跳過 A／B。
4. （選用）**Node.js ＋ clasp**：C 的 GAS 程式可用網頁編輯器貼，也可用 [clasp](https://github.com/google/clasp) 命令列建／推／更新（兩種建法在 `2-互動查詢bot（GAS）.md` 的 G1 都有寫）。

---

## 安裝順序（照這個走）

1. **`1-每日論文日報（Claude Routines）.md`** — 建兩個 Drive 資料夾、設 Routine、貼指令、驗收。（裝 A＋B）
2. **`2-互動查詢bot（GAS）.md`** — 把 GAS 程式部署成 webhook、接上 LINE、驗收。（裝 C；C 會去讀 B 存的資料夾）
3. **`附錄-用GAS當webhook的限制.md`** — 照做 C 之前先掃一遍 GAS 的坑，少踩雷。

---

## 檔案導覽

```
ed-newsbot-kit/
├── README.md                          ← 你正在看的入口
├── 1-每日論文日報（Claude Routines）.md   ← A+B 安裝教學（含可直接貼的 Routine 指令母本）
├── 2-互動查詢bot（GAS）.md               ← C 安裝教學（G1–G5）
├── code/
│   ├── Code.gs                         ← C 的 GAS 程式（全部設定走 Script Properties）
│   └── appsscript.json                 ← C 的 web app 設定
└── 附錄-用GAS當webhook的限制.md           ← GAS 當 webhook 的已知限制
```

---

## 安全提醒

- token / userId / webhook 秘密參數，一律放各平台的**設定欄**（Routine 環境變數、GAS Script Properties），**不要寫進程式碼、不要外傳**。
- 本套件所有 `<...>` 都是佔位符，請換成你自己的值。
- 互動 bot 用 GAS，有一個安全取捨（沒辦法驗 LINE 簽章），詳見附錄與 `2-...md`。對單人自用可接受；要開放多人請改用正規 serverless。
