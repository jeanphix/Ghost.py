# -*- coding: utf-8 -*-
import thread
import unittest
from casper import Casper
from app import app

PORT = 5000

thread.start_new_thread(app.run, (), {'port': PORT})
base_url = 'http://localhost:%s/' % PORT


class CapserTest(unittest.TestCase):

    casper = Casper()

    def test_open(self):
        ressources = self.casper.open(base_url)
        self.assertEqual(ressources[0].url, base_url)
        self.assertTrue("Test page" in self.casper.content)

    def test_http_status(self):
        ressources = self.casper.open("%sredirect-me" % base_url)
        self.assertEqual(ressources[0].http_status, 302)
        ressources = self.casper.open("%s404" % base_url)
        self.assertEqual(ressources[0].http_status, 404)

    def test_evaluate(self):
        self.casper.open(base_url)
        self.assertEqual(self.casper.evaluate("x='casper'; x;"), 'casper')

    def test_external_api(self):
        ressources = self.casper.open("%smootools" % base_url)
        self.assertEqual(len(ressources), 2)
        self.assertEqual(self.casper.evaluate("document.id('list')").type(),
            8)
        self.assertEqual(self.casper.evaluate("document.id('list')"),
            self.casper.evaluate("document.getElementById('list')"))

    def test_wait_for_selector(self):
        ressources = self.casper.open("%smootools" % base_url)
        self.casper.click("#button")
        # This is loaded via XHR :)
        ressources = self.casper.wait_for_selector("#list li:nth-child(2)")
        self.assertEqual(ressources[0].url, "%sitems.json" % base_url)

    def test_wait_for_text(self):
        ressources = self.casper.open("%smootools" % base_url)
        self.casper.click("#button")
        # This is loaded via XHR :)
        ressources = self.casper.wait_for_text("second item")
        self.assertEqual(ressources[0].url, "%sitems.json" % base_url)


if __name__ == '__main__':
    unittest.main()
