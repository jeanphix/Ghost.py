# -*- coding: utf-8 -*-
import os
import unittest

from ghost import GhostTestCase, Ghost
from app import app


PORT = 5000

base_url = 'http://localhost:%s/' % PORT


class GhostTest(GhostTestCase):
    port = PORT
    display = False

    def create_app(self):
        return app

    def test_open(self):
        page, ressources = self.ghost.open(base_url)
        self.assertEqual(page.url, base_url)
        self.assertTrue("Test page" in self.ghost.content)

    def test_http_status(self):
        page, ressources = self.ghost.open("%sredirect-me" % base_url)
        self.assertEqual(ressources[0].http_status, 302)
        page, ressources = self.ghost.open("%s404" % base_url)
        self.assertEqual(page.http_status, 404)

    def test_evaluate(self):
        self.ghost.open(base_url)
        self.assertEqual(self.ghost.evaluate("x='ghost'; x;")[0], 'ghost')

    def test_external_api(self):
        page, ressources = self.ghost.open("%smootools" % base_url)
        self.assertEqual(len(ressources), 2)
        self.assertEqual(self.ghost.evaluate("document.id('list')")[0].type(),
            8)
        self.assertEqual(self.ghost.evaluate("document.id('list')")[0],
            self.ghost.evaluate("document.getElementById('list')")[0])

    def test_wait_for_selector(self):
        page, ressources = self.ghost.open("%smootools" % base_url)
        success, ressources = self.ghost.click("#button")
        success, ressources = self.ghost\
            .wait_for_selector("#list li:nth-child(2)")
        self.assertEqual(ressources[0].url, "%sitems.json" % base_url)

    def test_wait_for_text(self):
        page, ressources = self.ghost.open("%smootools" % base_url)
        self.ghost.click("#button")
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
        }
        self.ghost.fill('#contact-form', values)
        page, ressources = self.ghost.fire_on('#contact-form', 'submit',
            expect_loading=True)
        self.assertEqual(ressources[0].http_status, 302)

    def test_open_timeout(self):
        self.assertRaises(Exception,
            self.ghost.open, "http://this.is.a.wrong.uri")

    def test_global_exists(self):
        self.ghost.open("%s" % base_url)
        self.assertTrue(self.ghost.global_exists('myGlobal'))

    def test_ressource_headers(self):
        page, ressources = self.ghost.open("%sitems.json" % base_url)
        self.assertEqual(page.headers['Content-Type'], 'application/json')

    def test_click_link(self):
        page, ressources = self.ghost.open("%s" % base_url)
        page, ressources = self.ghost.click('a', expect_loading=True)
        self.assertEqual(page.url, "%sform" % base_url)

    def test_cookies(self):
        self.ghost.open("%scookie" % base_url)
        self.assertEqual(len(self.ghost.cookies), 1)

    def test_delete_cookies(self):
        self.ghost.open("%scookie" % base_url)
        self.ghost.delete_cookies()
        self.assertEqual(len(self.ghost.cookies), 0)

    def test_wait_for_alert(self):
        self.ghost.open("%salert" % base_url)
        self.ghost.click('#alert-button')
        msg, ressources = self.ghost.wait_for_alert()
        self.assertEqual(msg, 'this is an alert')

    def test_confirm(self):
        self.ghost.open("%salert" % base_url)
        with Ghost.confirm():
            self.ghost.click('#confirm-button')
        msg, ressources = self.ghost.wait_for_alert()
        self.assertEqual(msg, 'you confirmed!')

    def test_no_confirm(self):
        self.ghost.open("%salert" % base_url)
        with Ghost.confirm(False):
            self.ghost.click('#confirm-button')
        msg, ressources = self.ghost.wait_for_alert()
        self.assertEqual(msg, 'you denied!')

    def test_confirm_callback(self):
        self.ghost.open("%salert" % base_url)
        with Ghost.confirm(callback=lambda: False):
            self.ghost.click('#confirm-button')
        msg, ressources = self.ghost.wait_for_alert()
        self.assertEqual(msg, 'you denied!')

    def test_prompt(self):
        self.ghost.open("%salert" % base_url)
        with Ghost.prompt('my value'):
            self.ghost.click('#prompt-button')
        value, ressources = self.ghost.evaluate('promptValue')
        self.assertEqual(value.toString(), 'my value')

    def test_prompt_callback(self):
        self.ghost.open("%salert" % base_url)
        with Ghost.prompt(callback=lambda: 'another value'):
            self.ghost.click('#prompt-button')
        value, ressources = self.ghost.evaluate('promptValue')
        self.assertEqual(value.toString(), 'another value')

    def test_capture_to(self):
        self.ghost.open(base_url)
        self.ghost.capture_to('test.png')
        self.assertTrue(os.path.isfile('test.png'))
        os.remove('test.png')

    def test_region_for_selector(self):
        self.ghost.open(base_url)
        self.assertEqual(self.ghost.region_for_selector('h1'),
            (8, 21, 391, 58))

    def test_capture_selector_to(self):
        self.ghost.open(base_url)
        self.ghost.capture_to('test.png', selector='h1')
        self.assertTrue(os.path.isfile('test.png'))
        os.remove('test.png')

    def test_set_field_value(self):
        self.ghost.open("%sform" % base_url)
        values = {
            'text': "Here is a sample text with ' \" quotes.",
            'email': 'my@awesome.email',
            'textarea': 'Here is a sample text.\nWith several lines.',
            'checkbox': True,
            "multiple-checkbox": "second choice",
            "radio": "first choice"
        }
        for field in values:
            self.ghost.set_field_value('[name=%s]' % field, values[field])

        for field in ['text', 'email', 'textarea']:
            value, resssources = self.ghost\
                .evaluate('document.getElementById("%s").value' % field)
            self.assertEqual(value.toString(), values[field])

        value, ressources = self.ghost.evaluate(
            'document.getElementById("checkbox").checked')
        self.assertEqual(value, True)

        value, ressources = self.ghost.evaluate(
            'document.getElementById("multiple-checkbox-first").checked')
        self.assertEqual(value, False)
        value, ressources = self.ghost.evaluate(
            'document.getElementById("multiple-checkbox-second").checked')
        self.assertEqual(value, True)

        value, ressources = self.ghost.evaluate(
            'document.getElementById("radio-first").checked')
        self.assertEqual(value, True)
        value, ressources = self.ghost.evaluate(
            'document.getElementById("radio-second").checked')
        self.assertEqual(value, False)

    def test_set_simple_file_field(self):
        self.ghost.open("%supload" % base_url)
        self.ghost.set_field_value('[name=simple-file]',
            os.path.join(os.path.dirname(__file__), 'static', 'blackhat.jpg'))
        page, ressources = self.ghost.fire_on('form', 'submit',
            expect_loading=True)
        file_path = os.path.join(
            os.path.dirname(__file__), 'uploaded_blackhat.jpg')
        self.assertTrue(os.path.isfile(file_path))
        os.remove(file_path)


if __name__ == '__main__':
    unittest.main()
