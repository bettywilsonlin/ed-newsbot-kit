// ED newsbot 互動查詢 bot — GAS webhook
//  • 直接打關鍵字  → 查「論文存檔資料夾」裡你存過的論文（回標題＋連結＋中文重點）
//  • All <關鍵字>  → 即時查全 PubMed 近一年最相關 5 篇（回標題＋連結）
//  • help          → 用法
// 部署為 Web App（執行身分：我；存取：任何人），LINE webhook 指向 /exec?k=<WEBHOOK_KEY>
//
// 所有設定走 Script Properties（不用改這支程式）：
//   LINE_CHANNEL_ACCESS_TOKEN  你的 LINE channel access token
//   OWNER_USER_ID              你的 LINE userId（只服務本人）
//   WEBHOOK_KEY                你自訂的隨機字（webhook 網址 ?k= 要帶同一串）
//   ARCHIVE_FOLDER_ID          論文存檔資料夾的 Google Drive folder ID
//
// 安全限制（GAS 讀不到 HTTP 標頭→無法驗 LINE 簽章）與替代防線，見「附錄-用GAS當webhook的限制.md」。

const EUTILS = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils';
const EXCLUSION = 'NOT (letter[pt] OR editorial[pt] OR comment[pt] OR news[pt])';
const MAX = 5;

function prop(k) { return PropertiesService.getScriptProperties().getProperty(k); }
function ok() { return ContentService.createTextOutput(JSON.stringify({ ok: true })).setMimeType(ContentService.MimeType.JSON); }
function qs(o) { return Object.keys(o).map(k => encodeURIComponent(k) + '=' + encodeURIComponent(o[k])).join('&'); }

function doPost(e) {
  if (!e || !e.parameter || e.parameter.k !== prop('WEBHOOK_KEY')) return ok(); // URL 秘密參數閘
  let body;
  try { body = JSON.parse(e.postData.contents); } catch (_) { return ok(); }
  const ownerId = prop('OWNER_USER_ID');
  for (const ev of (body.events || [])) {
    if (ev.type !== 'message' || !ev.message || ev.message.type !== 'text') continue;
    if (!ev.source || ev.source.userId !== ownerId) continue; // 只服務本人
    const text = (ev.message.text || '').trim();
    let out;
    if (/^help$/i.test(text)) out = helpText();
    else if (/^all\s+/i.test(text)) out = searchPubMed(text.replace(/^all\s+/i, '').trim());
    else out = searchArchive(text);
    replyLine(ev.replyToken, out);
  }
  return ok();
}

function helpText() {
  return [
    '📚 急診論文查詢 bot：',
    '',
    '• 直接打關鍵字（如 REBOA）→ 查你存過的日報，回標題＋連結＋中文重點',
    '• All <關鍵字>（如 All sepsis）→ 即時查全 PubMed 近一年最相關 5 篇，回標題＋連結',
    '• help → 這份說明',
  ].join('\n');
}

// ── archive 查詢：讀存檔資料夾所有 .md，整篇比對，回標題＋連結＋💡 ──
function searchArchive(keyword) {
  if (!keyword) return '打個關鍵字給我，例如 REBOA';
  const folderId = prop('ARCHIVE_FOLDER_ID');
  if (!folderId) return '（尚未設定 ARCHIVE_FOLDER_ID，請在 Script Properties 補上）';
  const kw = keyword.toLowerCase();
  const it = DriveApp.getFolderById(folderId).getFiles();
  const hits = [];
  while (it.hasNext()) {
    const f = it.next();
    const name = f.getName();
    if (!/\.md$/i.test(name)) continue;
    const date = (name.match(/(\d{4}-\d{2}-\d{2})/) || [])[1] || '';
    const content = f.getBlob().getDataAsString('UTF-8');
    for (const b of content.split(/\n-{3,}\n/)) {        // 以 --- 切成單篇
      if (!b.toLowerCase().includes(kw)) continue;        // 整篇（含 abstract）比對
      if (!/🔗/.test(b)) continue;                         // 跳過 frontmatter/標題段
      const title = (b.match(/(?:^|\n)\s*\d+\.\s*[^\n]+/) || [''])[0].trim();
      const link = (b.match(/🔗[^\n]*/) || [''])[0];
      const point = (b.match(/💡[^\n]*/) || [''])[0];
      hits.push({ date: date, text: [title, link, point].filter(Boolean).join('\n') });
    }
  }
  if (hits.length === 0) return '你存過的日報裡沒有「' + keyword + '」🔍';
  hits.sort(function (a, b) { return b.date.localeCompare(a.date); });      // 新到舊
  const top = hits.slice(0, MAX);
  const more = hits.length > MAX ? '\n\n（還有 ' + (hits.length - MAX) + ' 篇，關鍵字再縮小）' : '';
  return '🔍「' + keyword + '」在你的日報裡找到 ' + hits.length + ' 篇：\n\n' +
    top.map(function (h) { return '[' + h.date + ']\n' + h.text; }).join('\n\n──\n\n') + more;
}

// ── 即時 PubMed 查詢：只 esearch + esummary，回標題＋連結（不抓摘要、不叫 AI）──
function searchPubMed(keyword) {
  if (!keyword) return '打「All 關鍵字」，例如 All REBOA';
  const es = JSON.parse(UrlFetchApp.fetch(EUTILS + '/esearch.fcgi?' + qs({
    db: 'pubmed', term: '(' + keyword + ') ' + EXCLUSION, reldate: '365',
    datetype: 'edat', retmax: '50', retmode: 'json', sort: 'relevance',
  }), { muteHttpExceptions: true }).getContentText());
  const pmids = ((es.esearchresult || {}).idlist || []).slice(0, MAX);
  if (pmids.length === 0) return 'PubMed 近一年找不到「' + keyword + '」相關原著 🔍';
  const sum = JSON.parse(UrlFetchApp.fetch(EUTILS + '/esummary.fcgi?' + qs({
    db: 'pubmed', id: pmids.join(','), retmode: 'json',
  }), { muteHttpExceptions: true }).getContentText());
  const r = sum.result || {};
  const lines = pmids.map(function (id, i) {
    const title = ((r[id] && r[id].title) || '').replace(/\.\s*$/, '');
    return (i + 1) + '. ' + title + '\n🔗 https://pubmed.ncbi.nlm.nih.gov/' + id + '/';
  });
  return '🌐 PubMed「' + keyword + '」近一年最相關 ' + pmids.length + ' 篇（點連結看原文）：\n\n' + lines.join('\n\n');
}

function replyLine(replyToken, text) {
  UrlFetchApp.fetch('https://api.line.me/v2/bot/message/reply', {
    method: 'post', contentType: 'application/json',
    headers: { Authorization: 'Bearer ' + prop('LINE_CHANNEL_ACCESS_TOKEN') },
    muteHttpExceptions: true,
    payload: JSON.stringify({ replyToken: replyToken, messages: [{ type: 'text', text: text.slice(0, 4900) }] }),
  });
}
