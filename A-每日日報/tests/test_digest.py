import os, sys, json, re, datetime, tempfile, unittest
from unittest import mock
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import digest


class TestDigest(unittest.TestCase):
    def test_load_config_reads_env(self):
        env = {"LINE_CHANNEL_ACCESS_TOKEN": "tok", "DIGEST_TARGET_USER_ID": "U123",
               "DEDUP_DIR": "/tmp/dd", "ARCHIVE_DIR": "/tmp/ar", "AI_PROVIDER": "none"}
        with mock.patch.dict(os.environ, env, clear=True):
            cfg = digest.load_config()
        self.assertEqual(cfg["line_token"], "tok")
        self.assertEqual(cfg["target_id"], "U123")
        self.assertEqual(cfg["ai_provider"], "none")

    def test_load_config_missing_required_exits(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(SystemExit):
                digest.load_config()


if __name__ == "__main__":
    unittest.main()
