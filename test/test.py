import unittest

import cvc2git

class TestConvertLog(unittest.TestCase):
    def setUp(self):
        self.history = """
Name  : epdb:source
Branch: /foresight.rpath.org@fl:2-devel

tip-2 Jesse Zhang (zh.jesse@gmail.com) Thu Nov 24 22:26:24 2011
    Remove unused tarball

tip-1 Og Maciel (omaciel@foresightlinux.org) Fri Jan 29 12:41:57 2010
    Version bump and now pulling from bitbucket.

0.11-1 Antonio Meireles aka doniphon (sbin@reboot.sh) Mon Jan  5 18:02:31 2009
    the great migration to python-2.6 - promote for fl:2-devel
""".strip().splitlines()

    def test_version_startswith_not_num(self):
        commits = cvc2git.get_commits(self.history, {})
        self.assertEqual(3, len(commits))
        self.assertEqual("tip-2", commits[0].revision)
        self.assertEqual("0.11-1", commits[2].revision)

    def test_sort(self):
        commits = cvc2git.get_commits(self.history, {})
        cvc2git.sort_commits(commits)
        self.assertEqual("0.11-1", commits[0].revision)
        self.assertEqual("tip-2", commits[2].revision)

if __name__ == '__main__':
    unittest.main()
