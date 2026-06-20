"""ED newsbot 每日日報腳本（路2，適用各 AI）。純 Python 3 標準庫。"""
import os, sys, json, time, datetime, urllib.request, urllib.parse, urllib.error
import re

RATE_LIMIT = 0.4
CAP = 50
EXCLUSION = 'NOT (letter[pt] OR editorial[pt] OR comment[pt] OR news[pt])'
EUTILS = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils'
_DEDUP_RE = re.compile(r"^paperbot_pushed_(\d{4}-\d{2}-\d{2})\.json$")

def recent_dedup_filenames(names, today, days=8):
    out = []
    for n in names:
        m = _DEDUP_RE.match(n)
        if not m:
            continue
        try:
            d = datetime.date.fromisoformat(m.group(1))
        except ValueError:
            continue
        if 0 <= (today - d).days < days:
            out.append(n)
    return out

def parse_pushed_pmids(json_text):
    try:
        return list(json.loads(json_text).get("pushed_pmids", []))
    except (ValueError, AttributeError):
        return []

def load_config():
    def need(key):
        v = os.environ.get(key)
        if not v:
            sys.exit(f"缺少必填環境變數：{key}（值請設在 config.env，勿寫進程式）")
        return v
    return {
        "line_token": need("LINE_CHANNEL_ACCESS_TOKEN"),
        "target_id": need("DIGEST_TARGET_USER_ID"),
        "dedup_dir": need("DEDUP_DIR"),
        "archive_dir": os.environ.get("ARCHIVE_DIR", ""),   # 可空＝不存檔
        "ai_provider": os.environ.get("AI_PROVIDER", "none"),
        "ai_api_key": os.environ.get("AI_API_KEY", ""),
    }

def filter_with_abstract(papers):
    """丟掉 abstract 為 None 或空白（含只有空白字）者。"""
    return [p for p in papers if (p.get("abstract") or "").strip()]

def dedupe_pmids(pmids, seen):
    """保序去重：去掉重複與已存在於 seen 的 PMID；回傳去重後的列表。"""
    out, got = [], set()
    for p in pmids:
        if p in seen or p in got:
            continue
        got.add(p)
        out.append(p)
    return out

def build_paper_block(idx, title, pmid, point):
    """建構單篇論文的 Markdown 區塊，供 build_archive_markdown 組合用。
    格式契約：N. title / 🔗 URL / 💡 point（point 為 None 時省略）。
    block 內不含裸 ---，確保 C 的 split(/\\n-{3,}\\n/) 不會誤切。"""
    lines = [f"{idx}. {title}", f"🔗 https://pubmed.ncbi.nlm.nih.gov/{pmid}/"]
    if point:
        lines.append(f"💡 {point}")
    return "\n".join(lines)

def build_line_text(today, items, cap=CAP):
    """建構 LINE 訊息：≤cap 完整展示（標題+🔗+💡），>cap 則前 cap 篇完整、其餘只列標題+連結。0 篇時回心跳。
    日期格式 YYYY-MM-DD；heart beat 字串含「0 篇」；超量安全網段裡無 💡。"""
    d = today.isoformat()
    if not items:
        return f"📭 急診論文日報 {d}：今天 0 篇新論文（系統正常）"
    head = f"📬 急診論文日報 {d}（{min(len(items), cap)} 篇新）\n"
    full = items[:cap]
    body = "\n\n".join(build_paper_block(i + 1, it["title"], it["pmid"], it.get("point"))
                       for i, it in enumerate(full))
    out = head + "\n" + body
    overflow = items[cap:]
    if overflow:
        extra = "\n".join(f"{it['title']} 🔗 https://pubmed.ncbi.nlm.nih.gov/{it['pmid']}/"
                          for it in overflow)
        out += f"\n\n━━ 超量未列（明天會補完整摘要）━━\n{extra}"
    return out

def build_archive_markdown(today, items):
    """建構每日存檔 Markdown，輸出必須能被 C（GAS Code.gs）的 searchArchive 逐字解析。
    結構：YAML frontmatter → \\n---\\n → 各篇 block 以 \\n\\n---\\n\\n 分隔。
    frontmatter 結尾的 ---\\n 讓 C 的 split(/\\n-{3,}\\n/) 正確切出首篇（frontmatter 區無 🔗，會被過濾）。"""
    d = today.isoformat()
    head = (
        "---\n"
        f"title: ED newsbot {d}\n"
        "type: clipping\n"
        "source: 急診論文日報（PubMed）\n"
        f"created: {d}\n"
        "tags: [clipping, emergency_medicine]\n"
        "status: 待消化\n"
        "---\n\n"
        f"# 急診論文日報 {d}（{len(items)} 篇新）\n"
    )
    blocks = [build_paper_block(i + 1, it["title"], it["pmid"], it.get("point"))
              for i, it in enumerate(items)]
    # 篇與篇、以及 frontmatter 區與內容，皆以一行 --- 隔開（符合 C 的 split(/\n-{3,}\n/)）
    return head + "\n---\n" + "\n\n---\n\n".join(blocks) + "\n"

_PROMPT = ("你是急診醫師。只根據以下 abstract，用繁體中文寫 2-3 句臨床重點，"
           "不得加入 abstract 沒有的數字或結論：\n\n")

def _http_post_json(url, headers, payload):
    """HTTP POST 工具函式，共 _call_anthropic 與 _call_openai 複用。"""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))

def _call_anthropic(abstract, key):
    """呼叫 Anthropic API 生成 abstract 摘要。"""
    resp = _http_post_json(
        "https://api.anthropic.com/v1/messages",
        {"x-api-key": key, "anthropic-version": "2023-06-01",
         "content-type": "application/json"},
        {"model": "claude-opus-4-8", "max_tokens": 300,
         "messages": [{"role": "user", "content": _PROMPT + abstract}]})
    return resp["content"][0]["text"].strip()

def _call_openai(abstract, key):
    """呼叫 OpenAI API 生成 abstract 摘要。"""
    resp = _http_post_json(
        "https://api.openai.com/v1/chat/completions",
        {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        {"model": "gpt-4o", "max_tokens": 300,
         "messages": [{"role": "user", "content": _PROMPT + abstract}]})
    return resp["choices"][0]["message"]["content"].strip()

def write_summary(abstract, provider, api_key):
    """生成單篇 abstract 的中文臨床重點摘要。

    provider：'claude' / 'openai' / 'none'
    回傳：成功時回字串，任何例外自動降級回 None（呼叫端據此只給標題連結）。
    """
    try:
        if provider == "claude":
            return _call_anthropic(abstract, api_key)
        if provider == "openai":
            return _call_openai(abstract, api_key)
        return None
    except Exception:
        return None  # 自動降級：摘要失敗只給標題連結，不讓整支掛


# ── I/O 層：PubMed 抓取、LINE 推送、去重讀寫、存檔 ──────────────────────────

# 16 個 feed：前 11 為期刊 query，後 5 為主題 query（與路1 母本逐字一致）
FEEDS = [
    ("Resuscitation", '"Resuscitation"[Journal]'),
    ("Annals of Emergency Medicine", '"Annals of emergency medicine"[Journal]'),
    ("Academic Emergency Medicine", '"Academic emergency medicine"[Journal]'),
    ("American J of Emergency Medicine", '"The American journal of emergency medicine"[Journal]'),
    ("Emergency Medicine Journal", '"Emergency medicine journal"[Journal]'),
    ("Prehospital Emergency Care", '"Prehospital emergency care"[Journal]'),
    ("Critical Care", '"Critical care"[Journal]'),
    ("Intensive Care Medicine", '"Intensive care medicine"[Journal]'),
    ("Scand J Trauma Resusc Emerg Med", '"Scand J Trauma Resusc Emerg Med"[Journal]'),
    ("Eur J Emerg Med", '"Eur J Emerg Med"[Journal]'),
    ("World J Emerg Med", '"World J Emerg Med"[Journal]'),
    ("Resuscitative TEE", 'transesophageal echocardiography AND (cardiac arrest OR resuscitation OR periarrest OR shock) NOT (TAVI OR TAVR OR transcatheter)'),
    ("REBOA", '(REBOA OR "resuscitative endovascular balloon occlusion of the aorta" OR "resuscitative endovascular balloon occlusion")'),
    ("ECPR", '(ECPR OR "extracorporeal cardiopulmonary resuscitation" OR "extracorporeal CPR")'),
    ("TRM", '("crew resource management" OR "crisis resource management" OR "team resource management" OR "teamwork training") AND (emergency OR resuscitation OR "acute care" OR "patient safety")'),
    ("Simulation", '("simulation training"[MeSH Terms] OR "simulation-based education" OR "in situ simulation" OR "high-fidelity simulation") AND (emergency OR resuscitation OR "acute care" OR "critical care")'),
]


def _get(url):
    """底層 HTTP GET 工具函式，回傳解碼後字串。"""
    with urllib.request.urlopen(url, timeout=30) as r:
        return r.read().decode("utf-8")


def read_seen(dedup_dir, today):
    """讀取近 8 天的去重 JSON，回傳已推送 PMID 的 set（讓今天不重複推送舊文）。"""
    if not os.path.isdir(dedup_dir):
        return set()
    seen = set()
    for n in recent_dedup_filenames(os.listdir(dedup_dir), today):
        try:
            with open(os.path.join(dedup_dir, n), encoding="utf-8") as f:
                seen.update(parse_pushed_pmids(f.read()))
        except OSError:
            continue
    return seen


def esearch(query):
    """對 PubMed esearch 送出查詢，回傳過去 2 天符合條件的 PMID 列表（最多 30）。"""
    q = urllib.parse.urlencode({
        "db": "pubmed", "term": f"({query}) AND {EXCLUSION}",
        "datetype": "edat", "reldate": "2", "retmax": "30", "retmode": "json"})
    res = json.loads(_get(f"{EUTILS}/esearch.fcgi?{q}"))
    return res.get("esearchresult", {}).get("idlist", [])


def esummary(pmids):
    """批次查 PubMed esummary，回傳 {pmid: title} dict（title 去尾部句號與空白）。"""
    if not pmids:
        return {}
    q = urllib.parse.urlencode({"db": "pubmed", "id": ",".join(pmids), "retmode": "json"})
    res = json.loads(_get(f"{EUTILS}/esummary.fcgi?{q}")).get("result", {})
    return {p: (res.get(p, {}).get("title", "") or "").rstrip(". ") for p in pmids}


def efetch_abstract(pmid):
    """抓單篇 PubMed abstract 純文字；網路失敗時降級回 None（避免中斷整批）。"""
    q = urllib.parse.urlencode({"db": "pubmed", "id": pmid,
                                "rettype": "abstract", "retmode": "text"})
    try:
        txt = _get(f"{EUTILS}/efetch.fcgi?{q}").strip()
        return txt or None
    except urllib.error.URLError:
        return None


def fetch_new(seen):
    """跑完所有 FEEDS 的 PubMed 查詢，去重、抓 abstract，再過濾掉沒有 abstract 的篇章。
    每次 API 呼叫之間用 RATE_LIMIT 秒間隔，避免超過 NCBI 速率限制。"""
    all_pmids = []
    for _, query in FEEDS:
        try:
            all_pmids += esearch(query)
        except urllib.error.URLError:
            pass
        time.sleep(RATE_LIMIT)
    new = dedupe_pmids(all_pmids, seen)
    titles = esummary(new)
    time.sleep(RATE_LIMIT)
    papers = []
    for pmid in new:
        ab = efetch_abstract(pmid)
        time.sleep(RATE_LIMIT)
        papers.append({"pmid": pmid, "title": titles.get(pmid, ""), "abstract": ab, "point": None})
    return filter_with_abstract(papers)


def chunk_text(text, limit=4900):
    """把長訊息按段落（空行）切成每塊 ≤limit 字，盡量不切斷段落；單段超長才硬切。"""
    chunks, cur = [], ""
    for p in text.split("\n\n"):
        piece = (cur + "\n\n" + p) if cur else p
        if len(piece) <= limit:
            cur = piece
            continue
        if cur:
            chunks.append(cur)
            cur = ""
        while len(p) > limit:
            chunks.append(p[:limit])
            p = p[limit:]
        cur = p
    if cur:
        chunks.append(cur)
    return chunks or [""]


def push_line(token, target, text):
    """呼叫 LINE Messaging API push message；訊息截到 4900 字（LINE 上限 5000）。
    非 2xx 時印錯誤但不 raise，讓 main 仍能繼續寫去重與存檔。"""
    data = json.dumps({"to": target,
                       "messages": [{"type": "text", "text": text[:4900]}]}).encode("utf-8")
    req = urllib.request.Request(
        "https://api.line.me/v2/bot/message/push", data=data,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status
    except urllib.error.HTTPError as e:
        print("LINE 推送非 200：", e.code, e.read().decode("utf-8", "replace"))
        return e.code


def write_dedup(dedup_dir, today, pmids):
    """把今天推送的 PMID 列表寫成 JSON，供後續 read_seen 去重用。"""
    os.makedirs(dedup_dir, exist_ok=True)
    path = os.path.join(dedup_dir, f"paperbot_pushed_{today.isoformat()}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"date": today.isoformat(), "pushed_pmids": pmids}, f, ensure_ascii=False)


def write_archive(archive_dir, today, markdown):
    """把當日完整 Markdown 存成 `ED newsbot YYYY-MM-DD.md`，供 MyBrain 查詢。"""
    os.makedirs(archive_dir, exist_ok=True)
    path = os.path.join(archive_dir, f"ED newsbot {today.isoformat()}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(markdown)


def main():
    """主流程：讀設定 → 去重 → 抓新文 → AI 摘要 → 推 LINE → 寫去重 → 寫存檔。"""
    cfg = load_config()
    today = datetime.date.today()
    seen = read_seen(cfg["dedup_dir"], today)
    papers = fetch_new(seen)
    for p in papers:
        p["point"] = write_summary(p["abstract"], cfg["ai_provider"], cfg["ai_api_key"])
    full = papers[:CAP]
    last_status = None
    for chunk in chunk_text(build_line_text(today, papers)):
        last_status = push_line(cfg["line_token"], cfg["target_id"], chunk)
    print("LINE status:", last_status)
    if papers:
        write_dedup(cfg["dedup_dir"], today, [p["pmid"] for p in full])
    if papers and cfg["archive_dir"]:
        write_archive(cfg["archive_dir"], today, build_archive_markdown(today, full))


if __name__ == "__main__":
    main()
