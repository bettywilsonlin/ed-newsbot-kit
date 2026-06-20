# 路2：用腳本推播急診論文日報——設定與執行

> **一句話結論**：把 `digest.py` 在你電腦上跑起來，設定好 LINE Token 與幾個路徑，手動測試一次收到 LINE 訊息就算成功。成功後再去看排程文件。

適用對象：非工程師、只想照步驟做。腳本純 Python 3 標準函式庫，**不需安裝任何額外套件**。

---

## 目錄

1. [確認 Python 3 已安裝](#1-確認-python-3-已安裝)
2. [準備四個設定值](#2-準備四個設定值)
3. [決定要不要接 C（存檔到 MyBrain）](#3-決定要不要接-c存檔到-mybrain)
4. [選擇 AI 摘要模式](#4-選擇-ai-摘要模式)
5. [填寫 config.env](#5-填寫-configenv)
6. [手動跑一次，驗收結果](#6-手動跑一次驗收結果)
7. [下一步指引](#7-下一步指引)

---

## 1 確認 Python 3 已安裝

**結論**：先打一行指令確認有沒有，沒有的話按安裝鈕等它裝完。

### 步驟

1. 開「**終端機**」（Spotlight 搜尋「終端機」或「Terminal」）。
2. 輸入以下指令，按 Enter：

   ```bash
   python3 --version
   ```

3. 看到版本號（例如 `Python 3.12.4`）就代表已安裝，**可以跳過安裝步驟**。

4. 若跳出「要不要安裝開發者工具？」視窗（Xcode Command Line Tools），點「**安裝**」。
   - 大約 1 GB，視網路速度等 5–20 分鐘。
   - 裝完後**再打一次** `python3 --version`，看到版本號就 OK。

> **常見問題**：若出現 `command not found`，且沒有彈出安裝視窗，請到 [https://www.python.org/downloads/](https://www.python.org/downloads/) 下載安裝程式。

---

## 2 準備四個設定值

**結論**：在填設定之前，先把這四個值準備好，貼進去比較快。

### 2-1 LINE long-lived channel access token

這是讓腳本代替你推 LINE 訊息用的金鑰。

1. 前往 [LINE Developers Console](https://developers.line.biz/console/)，登入。
2. 找到你的 Messaging API channel，點進去。
3. 上方分頁點「**Messaging API**」。
4. 下滑找到「**Channel access token（long-lived）**」區塊，點「**Issue**」取得 token。
5. 複製那串很長的文字（`xxx...` 樣子，幾百個字元）。

> **注意**：這串 token 等於帳號密碼，不要讓別人看到，不要貼到公開地方。

### 2-2 你的 LINE userId

這是告訴腳本「要推給誰」的收件人 ID。

1. 同樣在 LINE Developers Console。
2. 上方分頁點「**Basic settings**」。
3. 下滑找到「**Your user ID**」欄位。
4. 複製那串 ID（以 `U` 開頭、共 33 個字元，例如 `U1234567890abcdef...`）。

> **注意**：這是「**Your user ID**」（你個人的使用者 ID），**不是** Channel ID（以 `C` 開頭那個），別拿錯了。

### 2-3 建立去重資料夾（避免同一篇論文重複推播）

腳本每天跑完後，會把今天推過的論文 PMID 記錄成一個 JSON 檔存在這個資料夾，下次跑時就知道哪些已推過。

1. 在你電腦上建一個資料夾，放在你記得住的地方，例如：
   ```
   /Users/<你的帳號>/ednews/dedup
   ```
2. 資料夾路徑要用**完整絕對路徑**（從 `/Users/` 開始），不能用 `~`。
3. 如果資料夾還不存在，也可以先填路徑——腳本第一次跑時會自動建立。

### 2-4 決定存檔路徑（先看第 3 節）

是否需要存檔，看下一節說明後再決定。

---

## 3 決定要不要接 C（存檔到 MyBrain）

**結論**：不需要 AI 搜尋功能就留空，需要就指向 Google Drive 桌面同步路徑。

### 什麼是「C」？

「C」是指 GAS（Google Apps Script）腳本，架設在 Google Sheets 上。它會讀取你存進 Google Drive 的論文 Markdown 檔，讓你可以在 Google Sheets 裡搜尋歷史論文。

### 要不要接？

| 狀況 | 建議 |
|---|---|
| 只要每天 LINE 收到論文就好 | `ARCHIVE_DIR` **留空**，不用接 C |
| 想在 Google Sheets 搜尋歷史論文 | 填 Google Drive 桌面同步路徑，再去設定 C |

### 接 C 時的存檔路徑

若要接 C，`ARCHIVE_DIR` 要指向 **Google Drive 桌面應用程式同步的本機路徑**，格式長這樣：

```
~/Library/CloudStorage/GoogleDrive-<你的Gmail帳號>/我的雲端硬碟/<你選的子資料夾>/
```

例如：

```
/Users/<你的帳號>/Library/CloudStorage/GoogleDrive-<你的Gmail>/我的雲端硬碟/ednews-archive/
```

> **兩個前提**：(1) 你的 Mac 必須已安裝並登入 Google Drive 桌面應用程式；(2) C 那端（GAS）要設定好才能搜尋。C 的設定細節請見「**路2-用腳本-排程與各平台.md**」。

---

## 4 選擇 AI 摘要模式

**結論**：不確定就先選 `none`，之後再改也很容易。

腳本的 `AI_PROVIDER` 有三個選項：

| 選項 | 效果 | 費用 |
|---|---|---|
| `none` | 每篇只給標題＋PubMed 連結，**不需要 API key** | 免費 |
| `claude` | 每篇附上 2–3 句繁體中文臨床重點（Anthropic API） | **按量計費**，與 Claude 訂閱方案是**不同帳號費用** |
| `openai` | 每篇附上 2–3 句繁體中文臨床重點（OpenAI API） | **按量計費**，與 ChatGPT 訂閱方案是**不同帳號費用** |

> **重要提醒**：選 `claude` 或 `openai` 時，需要自己到各平台申請「API key」，並加值付費才能使用。這與你平常訂閱 Claude.ai 或 ChatGPT 的費用**完全分開**，是另一套計費系統。若不確定，先用 `none` 測試整個流程沒問題再說。

### 取得 API key（選 `none` 可跳過）

- **Anthropic（claude）**：[https://console.anthropic.com/](https://console.anthropic.com/) → API Keys → Create Key
- **OpenAI（openai）**：[https://platform.openai.com/api-keys](https://platform.openai.com/api-keys) → Create new secret key

---

## 5 填寫 config.env

**結論**：複製範本、填進去、存檔，三步搞定。

### 步驟

1. 在終端機切到這個腳本所在的資料夾：

   ```bash
   cd "/Users/betty/Downloads/Claude agent/ed-newsbot-kit/A-每日日報"
   ```

   （把路徑換成你自己的實際位置）

2. 複製範本：

   ```bash
   cp config.example.env config.env
   ```

3. 用文字編輯器開啟 `config.env`（可以用 TextEdit，記得以純文字模式開；或直接在終端機打 `open -e config.env`）。

4. 把六個欄位填成你自己的值：

   ```env
   LINE_CHANNEL_ACCESS_TOKEN=<貼上你的 long-lived token>
   DIGEST_TARGET_USER_ID=<貼上你的 userId，U 開頭 33 字>
   DEDUP_DIR=<去重資料夾的完整路徑，例 /Users/你的帳號/ednews/dedup>
   ARCHIVE_DIR=<存檔資料夾完整路徑；不接 C 就留空>
   AI_PROVIDER=none
   AI_API_KEY=<選 none 就留空；選 claude/openai 才填 API key>
   ```

5. 存檔關閉。

> **注意**：`config.env` 含有你的 token 和 key，**不要** 把這個檔案傳給別人或上傳到 GitHub 等公開地方。`.gitignore` 已設定忽略此檔。

---

## 6 手動跑一次，驗收結果

**結論**：一行指令，手機看到 LINE 訊息就算成功。

### 指令

在終端機，確認在 `A-每日日報` 資料夾後，執行：

```bash
set -a; . ./config.env; set +a; python3 digest.py
```

這行指令做了三件事：
- `set -a; . ./config.env; set +a`：把 `config.env` 裡的設定值載入這個終端機工作階段
- `python3 digest.py`：執行腳本

### 預計等待時間

腳本會去 PubMed 查 16 個主題，每次查詢之間有短暫停頓（避免超過 NCBI 速率限制），整個流程大約需要 **3–8 分鐘**。

### 驗收三項

執行完成後，確認以下三項：

| 驗收項目 | 怎麼確認 |
|---|---|
| 1. LINE 手機收到訊息 | 打開 LINE，看 bot 有沒有傳來論文日報 |
| 2. 去重 JSON 檔已建立 | 到你設定的 `DEDUP_DIR` 資料夾，應有一個 `paperbot_pushed_<今天日期>.json` |
| 3.（若有填 `ARCHIVE_DIR`）存檔已建立 | 到 `ARCHIVE_DIR` 資料夾，應有一個 `ED newsbot <今天日期>.md` |

### 常見狀況說明

| 狀況 | 意思 | 處理方式 |
|---|---|---|
| 終端機印出 `LINE status: 200` | 推送成功 | 正常，等 LINE 通知 |
| `缺少必填環境變數：LINE_CHANNEL_ACCESS_TOKEN` | config.env 沒有正確載入，或欄位留空 | 確認指令有加 `set -a; . ./config.env; set +a;`，並確認欄位有填值 |
| `LINE 推送非 200：401` | Token 錯誤或過期 | 回 LINE Developers Console 重新取得 token |
| `LINE 推送非 200：400` | userId 填錯（最常見：填成 Channel ID） | 確認用的是「**Your user ID**」（`U` 開頭），不是 Channel ID（`C` 開頭）|
| 手機 0 篇新論文訊息 | 腳本正常，今天真的沒有新文章 | 正常，系統心跳（隔天再跑通常就有了）|
| 腳本跑完沒有 AI 摘要（只有標題+連結） | `AI_PROVIDER=none` 或 API key 有問題，腳本自動降級 | 正常行為；若要摘要，回第 4 節設定 |

---

## 7 下一步指引

**結論**：手動跑通後，去看對應的後續文件。

| 目標 | 去看 |
|---|---|
| 設定排程讓腳本每天自動執行 | `路2-用腳本-排程與各平台.md` |
| 記錄你這台電腦的設定，方便日後重現或移機 | `路2-自機重現紀錄.md`（填完可作為你的設定備忘錄） |
| 設定 C（Google Sheets 搜尋介面） | `路2-用腳本-排程與各平台.md`（C 的設定也在那份）|

---

*本文件對應腳本版本：`digest.py`（標準函式庫版，無第三方依賴）*
