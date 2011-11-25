# -*- coding: utf-8 -*-
import thread
import unittest
from ghost import Ghost
from app import app

PORT = 5000

thread.start_new_thread(app.run, (), {'port': PORT})
base_url = 'http://localhost:%s/' % PORT


class CapserTest(unittest.TestCase):

    ghost = Ghost()

    def test_open(self):
        ressources = self.ghost.open(base_url)
        self.assertEqual(ressources[0].url, base_url)
        self.assertTrue("Test page" in self.ghost.content)

    def test_http_status(self):
        ressources = self.ghost.open("%sredirect-me" % base_url)
        self.assertEqual(ressources[0].http_status, 302)
        ressources = self.ghost.open("%s404" % base_url)
        self.assertEqual(ressources[0].http_status, 404)

    def test_evaluate(self):
        self.ghost.open(base_url)
        self.assertEqual(self.ghost.evaluate("x='ghost'; x;")[0], 'ghost')

    def test_external_api(self):
        ressources = self.ghost.open("%smootools" % base_url)
        self.assertEqual(len(ressources), 2)
        self.assertEqual(self.ghost.evaluate("document.id('list')")[0].type(),
            8)
        self.assertEqual(self.ghost.evaluate("document.id('list')")[0],
            self.ghost.evaluate("document.getElementById('list')")[0])

    def test_wait_for_selector(self):
        ressources = self.ghost.open("%smootools" % base_url)
        success, ressources = self.ghost.click("#button")
        # This is loaded via XHR :)
        success, ressources = self.ghost\
            .wait_for_selector("#list li:nth-child(2)")
        self.assertEqual(ressources[0].url, "%sitems.json" % base_url)

    def test_wait_for_text(self):
        ressources = self.ghost.open("%smootools" % base_url)
        self.ghost.click("#button")
        # This is loaded via XHR :)
        success, ressources = self.ghost.wait_for_text("second item")
        self.assertEqual(ressources[0].url, "%sitems.json" % base_url)

    def test_fill(self):
        self.ghost.open("%scontact" % base_url)
        values = {
            'subject': 'Here is the subject',
            'email': 'my@awesome.email',
            'message': 'Here is my message.',
            'important': True
        }
        self.ghost.fill('#contact-form', values)
        for field in ['subject', 'email', 'message']:
            value, resssources = self.ghost\
                .evaluate('document.getElementById("%s").value' % field)
            self.assertEqual(value.toString(), values[field])
        value, ressources = self.ghost.evaluate(
            'document.getElementById("important").checked')
        self.assertEqual(value, True)

if __name__ == '__main__':
    unittest.main()
