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
        success, ressources = self.ghost.open(base_url)
        self.assertEqual(ressources[0].url, base_url)
        self.assertTrue("Test page" in self.ghost.content)

    def test_http_status(self):
        success, ressources = self.ghost.open("%sredirect-me" % base_url)
        self.assertEqual(ressources[0].http_status, 302)
        success, ressources = self.ghost.open("%s404" % base_url)
        self.assertEqual(ressources[0].http_status, 404)

    def test_evaluate(self):
        self.ghost.open(base_url)
        self.assertEqual(self.ghost.evaluate("x='ghost'; x;")[0], 'ghost')

    def test_external_api(self):
        success, ressources = self.ghost.open("%smootools" % base_url)
        self.assertEqual(len(ressources), 2)
        self.assertEqual(self.ghost.evaluate("document.id('list')")[0].type(),
            8)
        self.assertEqual(self.ghost.evaluate("document.id('list')")[0],
            self.ghost.evaluate("document.getElementById('list')")[0])

    def test_wait_for_selector(self):
        success, ressources = self.ghost.open("%smootools" % base_url)
        success, ressources = self.ghost.click("#button")
        # This is loaded via XHR :)
        success, ressources = self.ghost\
            .wait_for_selector("#list li:nth-child(2)")
        self.assertEqual(ressources[0].url, "%sitems.json" % base_url)

    def test_wait_for_text(self):
        success, ressources = self.ghost.open("%smootools" % base_url)
        self.ghost.click("#button")
        # This is loaded via XHR :)
        success, ressources = self.ghost.wait_for_text("second item")
        self.assertEqual(ressources[0].url, "%sitems.json" % base_url)

    def test_wait_for_timeout(self):
        self.ghost.open("%s" % base_url)
        self.assertRaises(Exception, self.ghost.wait_for_text, "undefined")

    def test_fill(self):
        self.ghost.open("%sform" % base_url)
        values = {
            'text': 'Here is a sample text.',
            'email': 'my@awesome.email',
            'textarea': 'Here is a sample text.\nWith several lines.',
            'checkbox': True,
            "radio": "first choice"
        }
        self.ghost.fill('#contact-form', values)
        for field in ['text', 'email', 'textarea']:
            value, resssources = self.ghost\
                .evaluate('document.getElementById("%s").value' % field)
            self.assertEqual(value.toString(), values[field])
        value, ressources = self.ghost.evaluate(
            'document.getElementById("checkbox").checked')
        self.assertEqual(value, True)
        value, ressources = self.ghost.evaluate(
            'document.getElementById("radio-first").checked')
        self.assertEqual(value, True)
        value, ressources = self.ghost.evaluate(
            'document.getElementById("radio-second").checked')
        self.assertEqual(value, False)

    def test_form_submission(self):
        self.ghost.open("%sform" % base_url)
        values = {
            'text': 'Here is a sample text.',
            'email': 'my@awesome.email',
            'textarea': 'Here is a sample text.\nWith several lines.',
            'checkbox': True,
            "radio": "first choice"
        }
        self.ghost.fill('#contact-form', values)
        self.ghost.fire_on('#contact-form', 'submit', except_loading=True)
        success, ressources = self.ghost.wait_for_page_loaded()
        self.assertEqual(ressources[0].http_status, 302)

    def test_open_timeout(self):
        self.assertRaises(Exception,
            self.ghost.open, "http://this.is.a.wrong.uri")


if __name__ == '__main__':
    unittest.main()
