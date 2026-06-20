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
