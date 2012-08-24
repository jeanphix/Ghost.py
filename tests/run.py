#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import unittest
import logging

from ghost import GhostTestCase, Ghost
from app import app


PORT = 5000

base_url = 'http://localhost:%s/' % PORT


class GhostTest(GhostTestCase):
    port = PORT
    display = False
    log_level = logging.INFO

    @classmethod
    def create_app(cls):
        return app

    def test_open(self):
        page, resources = self.ghost.open(base_url)
        self.assertEqual(page.url, base_url)
        self.assertTrue("Test page" in self.ghost.content)

    def test_http_status(self):
        page, resources = self.ghost.open("%sprotected" % base_url)
        self.assertEqual(resources[0].http_status, 403)
        page, resources = self.ghost.open("%s404" % base_url)
        self.assertEqual(page.http_status, 404)

    def test_evaluate(self):
        self.ghost.open(base_url)
        self.assertEqual(self.ghost.evaluate("x='ghost'; x;")[0], 'ghost')

    def test_external_api(self):
        page, resources = self.ghost.open("%smootools" % base_url)
        self.assertEqual(len(resources), 2)
        self.assertEqual(type(self.ghost.evaluate("document.id('list')")[0]),
            dict)

    def test_extra_resource_content(self):
        page, resources = self.ghost.open("%smootools" % base_url)
        self.assertIn('MooTools: the javascript framework',
            resources[1].content)

    def test_extra_resource_binaries(self):
        page, resources = self.ghost.open("%simage" % base_url)
        self.assertEqual(resources[1].content.__class__.__name__,
            'QByteArray')

    def test_wait_for_selector(self):
        page, resources = self.ghost.open("%smootools" % base_url)
        success, resources = self.ghost.click("#button")
        success, resources = self.ghost\
            .wait_for_selector("#list li:nth-child(2)")
        self.assertEqual(resources[0].url, "%sitems.json" % base_url)

    def test_wait_for_text(self):
        page, resources = self.ghost.open("%smootools" % base_url)
        self.ghost.click("#button")
        success, resources = self.ghost.wait_for_text("second item")
        self.assertEqual(resources[0].url, "%sitems.json" % base_url)

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
            self.assertEqual(value, values[field])
        value, resources = self.ghost.evaluate(
            'document.getElementById("checkbox").checked')
        self.assertEqual(value, True)
        value, resources = self.ghost.evaluate(
            'document.getElementById("radio-first").checked')
        self.assertEqual(value, True)
        value, resources = self.ghost.evaluate(
            'document.getElementById("radio-second").checked')
        self.assertEqual(value, False)

    def test_form_submission(self):
        self.ghost.open("%sform" % base_url)
        values = {
            'text': 'Here is a sample text.',
        }
        self.ghost.fill('#contact-form', values)
        page, resources = self.ghost.fire_on('#contact-form', 'submit',
            expect_loading=True)
        self.assertIn('form successfully posted', self.ghost.content)

    def test_global_exists(self):
        self.ghost.open("%s" % base_url)
        self.assertTrue(self.ghost.global_exists('myGlobal'))

    def test_resource_headers(self):
        page, resources = self.ghost.open(base_url)
        self.assertEqual(page.headers['Content-Type'], 'text/html; charset=utf-8')

    def test_click_link(self):
        page, resources = self.ghost.open("%s" % base_url)
        page, resources = self.ghost.click('a', expect_loading=True)
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
        msg, resources = self.ghost.wait_for_alert()
        self.assertEqual(msg, 'this is an alert')

    def test_confirm(self):
        self.ghost.open("%salert" % base_url)
        with Ghost.confirm():
            self.ghost.click('#confirm-button')
        msg, resources = self.ghost.wait_for_alert()
        self.assertEqual(msg, 'you confirmed!')

    def test_no_confirm(self):
        self.ghost.open("%salert" % base_url)
        with Ghost.confirm(False):
            self.ghost.click('#confirm-button')
        msg, resources = self.ghost.wait_for_alert()
        self.assertEqual(msg, 'you denied!')

    def test_confirm_callback(self):
        self.ghost.open("%salert" % base_url)
        with Ghost.confirm(callback=lambda: False):
            self.ghost.click('#confirm-button')
        msg, resources = self.ghost.wait_for_alert()
        self.assertEqual(msg, 'you denied!')

    def test_prompt(self):
        self.ghost.open("%salert" % base_url)
        with Ghost.prompt('my value'):
            self.ghost.click('#prompt-button')
        value, resources = self.ghost.evaluate('promptValue')
        self.assertEqual(value, 'my value')

    def test_prompt_callback(self):
        self.ghost.open("%salert" % base_url)
        with Ghost.prompt(callback=lambda: 'another value'):
            self.ghost.click('#prompt-button')
        value, resources = self.ghost.evaluate('promptValue')
        self.assertEqual(value, 'another value')

    def test_capture_to(self):
        self.ghost.open(base_url)
        self.ghost.capture_to('test.png')
        self.assertTrue(os.path.isfile('test.png'))
        os.remove('test.png')

    def test_region_for_selector(self):
        self.ghost.open(base_url)
        x1, y1, x2, y2 = self.ghost.region_for_selector('h1')
        self.assertEqual(x1, 8)
        self.assertEqual(y1, 21)
        self.assertEqual(x2, 791)

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
            self.assertEqual(value, values[field])

        value, resources = self.ghost.evaluate(
            'document.getElementById("checkbox").checked')
        self.assertEqual(value, True)

        value, resources = self.ghost.evaluate(
            'document.getElementById("multiple-checkbox-first").checked')
        self.assertEqual(value, False)
        value, resources = self.ghost.evaluate(
            'document.getElementById("multiple-checkbox-second").checked')
        self.assertEqual(value, True)

        value, resources = self.ghost.evaluate(
            'document.getElementById("radio-first").checked')
        self.assertEqual(value, True)
        value, resources = self.ghost.evaluate(
            'document.getElementById("radio-second").checked')
        self.assertEqual(value, False)

    def test_set_simple_file_field(self):
        self.ghost.open("%supload" % base_url)
        self.ghost.set_field_value('[name=simple-file]',
            os.path.join(os.path.dirname(__file__), 'static', 'blackhat.jpg'))
        page, resources = self.ghost.fire_on('form', 'submit',
            expect_loading=True)
        file_path = os.path.join(
            os.path.dirname(__file__), 'uploaded_blackhat.jpg')
        self.assertTrue(os.path.isfile(file_path))
        os.remove(file_path)

    def test_basic_http_auth_success(self):
        page, resources = self.ghost.open("%sbasic-auth" % base_url,
            auth=('admin', 'secret'))
        self.assertEqual(page.http_status, 200)

    def test_basic_http_auth_error(self):
        page, resources = self.ghost.open("%sbasic-auth" % base_url,
            auth=('admin', 'wrongsecret'))
        self.assertEqual(page.http_status, 401)

    def test_unsupported_content(self):
        page, resources = self.ghost.open("%ssend-file" % base_url)
        foo = open(os.path.join(os.path.dirname(__file__), 'static',
        'foo.tar.gz'), 'r').read(1024)
        self.assertEqual(resources[0].content, foo)


if __name__ == '__main__':
    unittest.main()
