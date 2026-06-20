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
