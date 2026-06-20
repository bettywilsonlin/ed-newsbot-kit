# C：互動查詢 bot（Google Apps Script）

在 LINE 打字就能查論文：

| 你打 | bot 做什麼 | 回什麼 |
|---|---|---|
| `REBOA`（直接打關鍵字）| 翻你的**論文存檔資料夾**（A＋B 每天存的）| 標題＋連結＋**中文重點** |
| `All REBOA`（前綴 `All`，不分大小寫）| **即時查全 PubMed** 近一年最相關 5 篇 | 標題＋連結（無中文重點，點進去看）|
| `help` | 用法 | 兩種查法說明 |

> **前提**：一個 Google 帳號（跑 GAS）、跟 A 同一個 LINE channel、已經做完 A＋B（這樣存檔資料夾裡才有東西可查；只想要即時查 PubMed 的話，archive 那半會回「沒有」但 `All` 仍可用）。
> **照做前先讀**：`附錄-用GAS當webhook的限制.md`。

---

## G1：建 GAS 專案，放程式（兩種建法，挑一種）

### 方法 A：GAS 網頁編輯器（不碰終端機，最簡單）

到 [drive.google.com](https://drive.google.com) → 新增 → **Google Apps Script**，然後：

1. 把 `code/Code.gs` 的內容貼進預設的 `Code.gs`（全選覆蓋）。
2. 左側若沒看到 `appsscript.json`：專案設定 ⚙ → 勾「在編輯器中顯示 appsscript.json 資訊清單檔案」→ 回編輯器把 `code/appsscript.json` 內容貼進去。

接著做 G2。

### 方法 B：clasp 命令列（會用終端機的人，建/推/更新都用指令）

[clasp](https://github.com/google/clasp) 是 Google 官方的 GAS 命令列工具，能在本機建專案、推程式、日後更新，不用每次去網頁貼。

**前置：**

```bash
# 1. 裝 Node.js 後，全域裝 clasp（釘 v3，免得裝到 v2 指令對不上）
npm install -g @google/clasp@3

# 2. 到 https://script.google.com/home/usersettings 把「Apps Script API」打開（clasp create 需要）

# 3. 登入。⚠️ 一定要登入「擁有論文存檔資料夾的那個 Google 帳號」，
#    否則部署後 DriveApp 讀不到資料夾（這個帳號錯了整個會白做）。
clasp login
```

> ⚠️ **clasp 版本**：本教學的 `clasp create-script`、`clasp redeploy` 是 **clasp v3.x** 的指令。舊版 v2 的對應指令不同（建立是 `clasp create`、且沒有 `redeploy`）——若你之前裝過舊版，先 `npm install -g @google/clasp@3` 升上來再照做。用 `clasp --version` 確認。

> clasp 切帳號：若 `clasp login` 已登入別的帳號、又沒有覆蓋選項，先把舊登入檔移開再重登：
> `mv ~/.clasprc.json ~/.clasprc.json.bak && clasp login`。登完它會印「You are logged in as <你的 email>」，**確認是對的帳號**再往下。

**建立 ＋ 推程式：**

```bash
# 在一個空資料夾裡（等下放 code/ 的兩個檔）
clasp create-script --title "ED newsbot 互動bot" --type standalone
# create 會自己產一個 appsscript.json；用本套件 code/ 的兩個檔覆蓋進這個資料夾，再推：
clasp push --force
```

**clasp 能代 / 不能代（誠實講）：**

| clasp 幫你做 | clasp 做不到（仍要你手動）|
|---|---|
| 建專案、推 `Code.gs`/`appsscript.json`、日後 `clasp push` 更新 | **G2 設 Script Properties**（密鑰，只能在網頁設定欄或一次性函式裡填）|
| 列/管理部署 | **G3 的 OAuth 授權**（按「允許」要瀏覽器）|
| | **G4 接 LINE webhook**（LINE 後台只能你登）|

所以走方法 B 也是：clasp 把 G1（＋日後更新）包掉，**G2～G5 照下面繼續、一樣要你親手**。

---

## G2：設 4 個 Script Properties

GAS 編輯器左側 **⚙ 專案設定** → 捲到「**指令碼屬性**」→ 新增 4 筆：

| 屬性 | 值 |
|---|---|
| `LINE_CHANNEL_ACCESS_TOKEN` | 你的 LINE channel access token（跟 A 同一把）|
| `OWNER_USER_ID` | 你的 LINE userId（U 開頭 33 字；跟 A 的 `DIGEST_TARGET_USER_ID` 同一個）|
| `WEBHOOK_KEY` | 你自己想一串隨機字（16+ 字母數字，等下 LINE 網址要用同一串）|
| `ARCHIVE_FOLDER_ID` | 你的「論文存檔資料夾」folder ID（A 的 Step 0 那個）|

> 產隨機字：終端機 `openssl rand -hex 16`，或隨手敲一長串英數字。

---

## G3：部署成 Web App

右上 **部署 → 新增部署** → 齒輪選「**網頁應用程式**」→ 執行身分「**我**」、存取權「**任何人**」→ 部署。

- 第一次會跳**授權**（要存取 Drive 讀檔＋連外）→ 選你的帳號 → 進階 → 繼續 → 允許。
- 複製拿到的網址：`https://script.google.com/macros/s/XXXX/exec`。

> ⚠️ 存取權一定要「**任何人**」。設成「僅自己／有 Google 帳號的人」→ LINE 的匿名請求會被轉去 Google 登入頁，webhook 永遠收不到。

---

## G4：接上 LINE webhook

到 [LINE Developers](https://developers.line.biz) → 你的 channel → **Messaging API** 分頁 → **Webhook settings**：

1. Webhook URL 填：`你的exec網址?k=你的WEBHOOK_KEY`
   （例：`https://script.google.com/macros/s/XXXX/exec?k=你在G2設的WEBHOOK_KEY`）
2. 按 **Verify**。
   - **若回 302 錯誤 → 不用理它**。GAS 的 `/exec` 對 POST 會先回 302 轉址才給內容，LINE 的 Verify 很嚴格會報錯，但**實際送訊息 LINE 會跟著轉址、仍會送達**。真正的驗收是 G5 用手機傳訊息。
3. 打開「**Use webhook**」開關。
4. 到 **LINE Official Account Manager**（manager.line.biz）→ 設定 → 回應設定 → 把「**自動回應訊息**」**關掉**（不然每次都會多一則制式罐頭回覆）；「Webhook」保持開。

---

## G5：手機驗收

打開 LINE，傳訊息給你的官方帳號：

1. `help` → 應回「📚 急診論文查詢 bot：…」（且只有這一則，沒有罐頭）
2. 一個存檔裡有的關鍵字（如 `ECPR`）→ 回標題＋連結＋中文重點
3. 一個沒存過的詞 → 回「你存過的日報裡沒有…」
4. `All sepsis` → 數秒內回 5 篇 PubMed 標題＋連結
5. 用**別的 LINE 帳號**傳 → bot 不回（只服務本人）

全過就完成了 🎉

---

## 之後要改程式怎麼生效

GAS 的 web app 認「**部署版本**」——只更新程式碼、不發新版本的話，線上 webhook 還是跑舊碼。改完 `Code.gs` 後二選一：

- **網頁**：部署 → 管理部署 → 編輯（鉛筆）→ 版本：**新版本** → 部署。
- **clasp**：
  ```bash
  clasp push                       # 推新程式碼
  clasp list-deployments           # 找到 web app 的 deploymentId（AKfyc... 那個）
  clasp redeploy <deploymentId> -d "更新說明"   # 把該部署更到新版本（網址不變）
  ```
  （`clasp redeploy` 更新「同一個部署」，所以 exec 網址不變、LINE 那邊不用重設。）

---

## 安全取捨（重要）

GAS 讀不到 HTTP 標頭，所以**沒辦法驗 LINE 的簽章**。本 bot 改用三層替代防線：webhook URL 的 `?k=` 秘密參數、只回應本人 userId、reply token 由 LINE 簽發（偽造請求拿不到有效 token）。對**單人自用**夠用；最壞情況是秘密網址外洩被狂打、燒當天配額（騷擾級，非資料外洩）。要開放多人或回傳敏感內容，請改用能驗簽章的正規 serverless（如 Cloudflare Workers）。細節見 `附錄-用GAS當webhook的限制.md`。
