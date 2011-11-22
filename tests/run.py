# -*- coding: utf-8 -*-
import unittest
from casper import Casper


class CapserTest(unittest.TestCase):

    casper = Casper()

    def test_open(self):
        ressources = self.casper.open(u"http://jeanphi.fr")
        self.assertEqual(ressources[0].url, u"http://jeanphi.fr/")
        self.assertEqual(ressources[0].http_status, 301)
        self.assertEqual(ressources[1].url, u"http://www.jeanphi.fr/")
        self.assertEqual(ressources[1].http_status, 200)
        self.assertTrue("jeanphix" in self.casper.content)

    def test_evaluate(self):
        self.casper.open(u"http://jeanphi.fr")
        self.assertEqual(
            self.casper.evaluate("x='casper'; x;"),
            'casper'
        )

    def test_evaluate_with_varying_datas(self):
        self.casper.open(u"http://jeanphi.fr")
        self.assertEqual(
            self.casper.evaluate("x='%s'; x;" % 'casper'),
            'casper'
        )

if __name__ == '__main__':
    unittest.main()
