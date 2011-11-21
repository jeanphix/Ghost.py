import unittest
from casper import Casper


class CapserTest(unittest.TestCase):
    casper = Casper()

    def test_open(self):
        self.casper.open("http://jeanphi.fr")
        self.assertTrue("jeanphix" in self.casper.content)

if __name__ == '__main__':
    unittest.main()
