import os
import tempfile
import unittest
from unittest.mock import patch

from store import db


class StoreEditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_patch = patch.object(db, "DB_PATH", os.path.join(self.tmp.name, "pipeline.db"))
        self.db_patch.start()

    def tearDown(self):
        self.db_patch.stop()
        self.tmp.cleanup()

    def test_edit_title_changes_id_and_preserves_created_at(self):
        item = {"title": "原来的完整标题", "body": "正文", "time": "2026-07-15 09:00"}
        db.save_article(item)
        old_id = db._aid(item["title"])
        new_item = {**item, "title": "修改后的完整标题", "body": "新正文", "qc_level": "green"}
        new_id = db.update_article(old_id, new_item, "未发")
        rows = db.all_articles()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], new_id)
        self.assertEqual(rows[0]["created_at"], "2026-07-15 09:00")


if __name__ == "__main__":
    unittest.main()
