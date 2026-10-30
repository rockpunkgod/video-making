"""Verify the bounded supplement reaches the current writing consumer."""
import unittest
from core.registry import Registry, ROOT
from scripts.generate_assets import build


class CourseWritingSupplementTests(unittest.TestCase):
    def test_current_consumer_and_historical_boundary(self):
        current = Registry()
        baseline = current.index['source_baseline']['commit']
        assets = build(current)
        path = 'gaokao-writing/references/course-update-2027.md'
        self.assertIn('course-update-2027.md', assets['gaokao-writing/SKILL.md'])
        self.assertTrue(assets[path].endswith(
            (ROOT/'docs/course-writing-update-2027-20261030.md').read_text(encoding='utf-8')))
        self.assertEqual(current.index['source_baseline']['commit'], baseline)
        historical = build(Registry(snapshot_commit='1c388a0596b13935ae7c6a1af00834915a8efa33'))
        self.assertNotIn(path, historical)
        self.assertNotIn('course-update-2027.md', historical['gaokao-writing/SKILL.md'])


if __name__ == '__main__':
    unittest.main()
