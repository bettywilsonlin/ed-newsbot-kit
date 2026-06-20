import os, sys, json, re, datetime, tempfile, unittest
from unittest import mock
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import digest


# 模組層級函式（放 class 之外）：鏡像 Code.gs 行 65-71 的 searchArchive
def _c_parser_extract(md_content):
    """以 \n---\n 切篇、需含 🔗、抓 N./🔗/💡（重現 C 的 searchArchive）。"""
    hits = []
    for b in re.split(r"\n-{3,}\n", md_content):
        if "🔗" not in b:
            continue
        title = re.search(r"(?:^|\n)\s*\d+\.\s*[^\n]+", b)
        link = re.search(r"🔗[^\n]*", b)
        point = re.search(r"💡[^\n]*", b)
        if title and link:
            hits.append({"title": title.group(0).strip(),
                         "link": link.group(0),
                         "point": point.group(0) if point else ""})
    return hits


class TestDigest(unittest.TestCase):
    def test_recent_dedup_filenames_filters_by_name_date(self):
        today = datetime.date(2026, 6, 21)
        names = [
            "paperbot_pushed_2026-06-21.json",  # 今天 → 留
            "paperbot_pushed_2026-06-15.json",  # 6 天前 → 留
            "paperbot_pushed_2026-06-10.json",  # 11 天前 → 丟
            "unrelated.json",                   # 不符前綴 → 丟
        ]
        got = digest.recent_dedup_filenames(names, today, days=8)
        self.assertIn("paperbot_pushed_2026-06-21.json", got)
        self.assertIn("paperbot_pushed_2026-06-15.json", got)
        self.assertNotIn("paperbot_pushed_2026-06-10.json", got)
        self.assertNotIn("unrelated.json", got)

    def test_parse_pushed_pmids(self):
        txt = '{"date":"2026-06-21","pushed_pmids":["111","222"]}'
        self.assertEqual(digest.parse_pushed_pmids(txt), ["111", "222"])

    def test_parse_pushed_pmids_bad_json_returns_empty(self):
        self.assertEqual(digest.parse_pushed_pmids("not json"), [])

    def test_load_config_reads_env(self):
        env = {"LINE_CHANNEL_ACCESS_TOKEN": "tok", "DIGEST_TARGET_USER_ID": "U123",
               "DEDUP_DIR": "/tmp/dd", "ARCHIVE_DIR": "/tmp/ar", "AI_PROVIDER": "none"}
        with mock.patch.dict(os.environ, env, clear=True):
            cfg = digest.load_config()
        self.assertEqual(cfg["line_token"], "tok")
        self.assertEqual(cfg["target_id"], "U123")
        self.assertEqual(cfg["ai_provider"], "none")
        self.assertEqual(cfg["dedup_dir"], "/tmp/dd")
        self.assertEqual(cfg["archive_dir"], "/tmp/ar")

    def test_load_config_missing_required_exits(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(SystemExit):
                digest.load_config()

    def test_filter_with_abstract_drops_empty(self):
        papers = [
            {"pmid": "1", "title": "a", "abstract": "real abstract"},
            {"pmid": "2", "title": "b", "abstract": ""},
            {"pmid": "3", "title": "c", "abstract": None},
            {"pmid": "4", "title": "d", "abstract": "   "},
        ]
        got = digest.filter_with_abstract(papers)
        self.assertEqual([p["pmid"] for p in got], ["1"])

    def test_dedupe_pmids_preserves_order_and_removes_seen(self):
        pmids = ["1", "2", "2", "3", "1"]
        seen = {"3"}
        self.assertEqual(digest.dedupe_pmids(pmids, seen), ["1", "2"])

    def test_archive_markdown_is_parseable_by_c(self):
        today = datetime.date(2026, 6, 21)
        items = [
            {"pmid": "111", "title": "REBOA in trauma", "abstract": "x", "point": "重點一"},
            {"pmid": "222", "title": "ECPR outcomes", "abstract": "y", "point": "重點二"},
        ]
        md = digest.build_archive_markdown(today, items)
        self.assertIn("2026-06-21", md)
        hits = _c_parser_extract(md)
        self.assertEqual(len(hits), 2)
        self.assertIn("REBOA in trauma", hits[0]["title"])
        self.assertIn("https://pubmed.ncbi.nlm.nih.gov/111/", hits[0]["link"])
        self.assertIn("重點一", hits[0]["point"])

    def test_archive_block_without_point_still_has_link(self):
        today = datetime.date(2026, 6, 21)
        items = [{"pmid": "333", "title": "No summary paper", "abstract": "z", "point": None}]
        md = digest.build_archive_markdown(today, items)
        hits = _c_parser_extract(md)
        self.assertEqual(len(hits), 1)
        self.assertIn("https://pubmed.ncbi.nlm.nih.gov/333/", hits[0]["link"])


if __name__ == "__main__":
    unittest.main()
