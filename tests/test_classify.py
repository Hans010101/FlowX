import unittest

from hotspot.classify import classify
from hotspot.fetch import HotItem


class ClassifyTests(unittest.TestCase):
    def test_specific_multi_hit_beats_earlier_generic_hit(self):
        tracks = {
            "yule": {"name": "娱乐", "keywords": ["曝光", "回应"]},
            "keji": {"name": "科技", "keywords": ["iPhone", "售价", "苹果手机"]},
        }
        hit = classify(HotItem(title="iPhone 新机售价曝光", source="test"), tracks)
        self.assertEqual(hit[0], "keji")

    def test_tie_preserves_track_order(self):
        tracks = {
            "first": {"name": "一", "keywords": ["发布"]},
            "second": {"name": "二", "keywords": ["发布"]},
        }
        self.assertEqual(classify(HotItem(title="新品发布", source="test"), tracks)[0], "first")

    def test_no_hit_returns_none(self):
        self.assertIsNone(classify(HotItem(title="无关标题", source="test"), {
            "sports": {"name": "体育", "keywords": ["足球"]}
        }))


if __name__ == "__main__":
    unittest.main()
