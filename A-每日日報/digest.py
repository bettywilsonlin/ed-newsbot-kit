"""ED newsbot 每日日報腳本（路2，適用各 AI）。純 Python 3 標準庫。"""
import os, sys, json, time, datetime, urllib.request, urllib.parse, urllib.error

RATE_LIMIT = 0.4
CAP = 50
EXCLUSION = 'NOT (letter[pt] OR editorial[pt] OR comment[pt] OR news[pt])'
EUTILS = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils'

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
