import unittest

from quality.check import rule_check


class QualityRuleTests(unittest.TestCase):
    def test_severe_title_tail_is_blocking(self):
        problems, _, severe = rule_check({
            "title": "这是一个明显断尾的", "body": "正文" * 250, "image": "cover.jpg"
        })
        self.assertTrue(severe)
        self.assertTrue(any("标题断尾" in p for p in problems))


if __name__ == "__main__":
    unittest.main()
