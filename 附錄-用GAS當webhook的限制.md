# 附錄：用 GAS 當 LINE webhook 的已知限制

GAS（Google Apps Script）當 webhook 很省事——免伺服器、免帳單、跟 Google Drive 原生整合——但它有一票「跟一般伺服器不一樣」的坑。**照本套件做 C（互動 bot）之前先掃過，少踩雷。**

| # | 限制 | 影響 / 對策 |
|---|---|---|
| 1 | **`doPost(e)` 讀不到 HTTP 標頭** | 拿不到 `X-Line-Signature` → **無法驗 LINE 簽章**。對策：webhook URL 帶秘密參數 `?k=<隨機字>`，`doPost` 比對 `e.parameter.k`；再加「只回應本人 userId」。安全強度低於能驗簽章的平台。 |
| 2 | **`/exec` 對 POST 會回 302 轉址**到 `googleusercontent.com` 才給內容 | LINE 後台「**Verify**」會因此報「非 200（302）」——**這是假警報**，LINE 實際送訊息會跟著轉址、仍送達。但「不跟轉址」的工具（curl 預設、某些監控）會誤判失敗。用 curl 測得加 `--post302`，且注意轉址 token 是一次性、無法直接重打。 |
| 3 | **同步、無背景執行**（沒有 Cloudflare Workers 的 `waitUntil`）| `doPost` 得「整段跑完才回 200」，沒辦法「先秒回、再背景慢慢做」。慢工會卡住 webhook、被 LINE 判逾時重送。**本套件因此把工作壓到 1～3 秒內**：查預先存好的 archive、即時查只回標題連結（不抓摘要、不叫 AI）。若你想加「即時查＋AI 寫摘要」，量過約 15～19 秒——GAS 撐不住，要改架構或換平台。 |
| 4 | **部署存取權必須「任何人」(`ANYONE_ANONYMOUS`)** | 設成「僅自己／有 Google 帳號的人」→ 匿名的 LINE POST 被轉去 **Google 登入頁**，webhook 永遠收不到。判別：POST `/exec` 看轉址去 `googleusercontent`（對）還是 `accounts.google.com`（錯）。 |
| 5 | **改程式不會自動生效** | 存檔／`clasp push` 只更新「草稿」。要「**管理部署 → 編輯 → 版本：新版本**」才會讓線上 webhook 跑到新碼。常見坑：改完發現沒變＝忘了發新版本。 |
| 6 | **執行配額 / 時間上限** | UrlFetchApp 與執行次數有**每日配額**（個人帳號約每天 2 萬次 UrlFetch）；單次執行上限 6 分鐘。被狂打會當天耗盡。 |
| 7 | **沒有原生環境變數 / Secret 管理** | 用 **Script Properties** 存 token / key（別寫進程式碼）。注意：同專案的編輯者都看得到。 |
| 8 | **`e` 物件只有 `postData.contents` ＋ `parameter`（query string）** | 沒有 method、headers、raw request。只能靠 body JSON ＋ URL 參數判斷。 |
| 9 | **reply token 一次性、約 1 分鐘過期** | 若先做很久的工才 reply，token 可能已過期。慢流程要改用 **push API**（但 push 需另存對方 userId，且不是「回覆當下那則訊息」）。 |
| 10 | **GAS 跑在「部署者」帳號** | `DriveApp` 等存取的是**部署者的 Drive**。要讀某個資料夾，專案就得建在**該資料夾擁有者的 Google 帳號**底下。（用 clasp 時尤其要確認登入對帳號。）|

---

**一句話**：GAS 適合「**收到訊息 → 1～3 秒內查好現成資料 → 回覆**」這種輕量同步 webhook。一旦需要「重運算、背景任務、嚴格簽章驗證、高併發、多人開放」，就該換 Cloudflare Workers / Cloud Functions 這類正規 serverless。
