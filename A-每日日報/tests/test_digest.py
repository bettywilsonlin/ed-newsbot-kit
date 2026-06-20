import os, sys, json, re, datetime, tempfile, unittest
from unittest import mock
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import digest


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


if __name__ == "__main__":
    unittest.main()
