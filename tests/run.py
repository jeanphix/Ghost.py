#!/usr/bin/env python
# -*- coding: utf-8 -*-


import sys
PY3 = sys.version > '3'
import os
import logging
import unittest
try:
    import cookielib
except ImportError:
    from http import cookiejar as cookielib

from app import app
from ghost import GhostTestCase, Ghost


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

    def test_open_page_with_no_cache_headers(self):
        page, resources = self.ghost.open("%sno-cache" % base_url)
        self.assertIsNotNone(page.content)
        self.assertIn("cache for me", page.content)

    def test_open_403(self):
        page, resources = self.ghost.open("%sprotected" % base_url)
        self.assertEqual(resources[0].http_status, 403)

    def test_open_404(self):
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

    def test_settimeout(self):
        page, resources = self.ghost.open("%ssettimeout" % base_url)
        result, _ = self.ghost.evaluate("document.getElementById('result').innerHTML")
        self.assertEqual(result, 'Bad')
        self.ghost.sleep(4)
        result, _ = self.ghost.evaluate("document.getElementById('result').innerHTML")
        self.assertEqual(result, 'Good')

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
            'selectbox': 'two',
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
            "document.querySelector('option[value=two]').selected;")
        self.assertTrue(value)
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
        page, resources = self.ghost.call('#contact-form', 'submit',
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

    def test_save_load_cookies(self):
        self.ghost.delete_cookies()
        self.ghost.open("%sset/cookie" % base_url)
        self.ghost.save_cookies('testcookie.txt')
        self.ghost.delete_cookies()
        self.ghost.load_cookies('testcookie.txt')
        self.ghost.open("%sget/cookie" % base_url)
        self.assertTrue( 'OK' in self.ghost.content )

    def test_load_cookies_expire_is_none(self):
        self.ghost.delete_cookies()
        jar = cookielib.CookieJar()
        cookie = cookielib.Cookie(version=0, name='Name', value='1', port=None,
                                  port_specified=False,
                                  domain='www.example.com',
                                  domain_specified=False,
                                  domain_initial_dot=False, path='/',
                                  path_specified=True, secure=False,
                                  expires=None, discard=True, comment=None,
                                  comment_url=None, rest={'HttpOnly': None},
                                  rfc2109=False)
        jar.set_cookie(cookie)
        self.ghost.load_cookies(jar)

    def test_wait_for_alert(self):
        self.ghost.open("%salert" % base_url)
        self.ghost.click('#alert-button')
        msg, resources = self.ghost.wait_for_alert()
        self.assertEqual(msg, 'this is an alert')

    def test_confirm(self):
        self.ghost.open("%salert" % base_url)
        with self.ghost.confirm():
            self.ghost.click('#confirm-button')
        msg, resources = self.ghost.wait_for_alert()
        self.assertEqual(msg, 'you confirmed!')

    def test_no_confirm(self):
        self.ghost.open("%salert" % base_url)
        with self.ghost.confirm(False):
            self.ghost.click('#confirm-button')
        msg, resources = self.ghost.wait_for_alert()
        self.assertEqual(msg, 'you denied!')

    def test_confirm_callable(self):
        self.ghost.open("%salert" % base_url)
        with self.ghost.confirm(lambda: False):
            self.ghost.click('#confirm-button')
        msg, resources = self.ghost.wait_for_alert()
        self.assertEqual(msg, 'you denied!')

    def test_prompt(self):
        self.ghost.open("%salert" % base_url)
        with self.ghost.prompt('my value'):
            self.ghost.click('#prompt-button')
        value, resources = self.ghost.evaluate('promptValue')
        self.assertEqual(value, 'my value')

    def test_prompt_callable(self):
        self.ghost.open("%salert" % base_url)
        with self.ghost.prompt(lambda: 'another value'):
            self.ghost.click('#prompt-button')
        value, resources = self.ghost.evaluate('promptValue')
        self.assertEqual(value, 'another value')

    def test_popup_messages_collection(self):
        self.ghost.open("%salert" % base_url, default_popup_response=True)
        self.ghost.click('#confirm-button')
        self.assertIn('this is a confirm', self.ghost.popup_messages)
        self.ghost.click('#prompt-button')
        self.assertIn('Prompt ?', self.ghost.popup_messages)
        self.ghost.click('#alert-button')
        self.assertIn('this is an alert', self.ghost.popup_messages)

    def test_prompt_default_value_true(self):
        self.ghost.open("%salert" % base_url, default_popup_response=True)
        self.ghost.click('#confirm-button')
        msg, resources = self.ghost.wait_for_alert()
        self.assertEqual(msg, 'you confirmed!')

    def test_prompt_default_value_false(self):
        self.ghost.open("%salert" % base_url, default_popup_response=False)
        self.ghost.click('#confirm-button')
        msg, resources = self.ghost.wait_for_alert()
        self.assertEqual(msg, 'you denied!')

    def test_capture_to(self):
        self.ghost.open(base_url)
        self.ghost.capture_to('test.png')
        self.assertTrue(os.path.isfile('test.png'))
        os.remove('test.png')

    def test_region_for_selector(self):
        self.ghost.open(base_url)
        x1, y1, x2, y2 = self.ghost.region_for_selector('h1')
        self.assertEqual(x1, 0)
        self.assertEqual(y1, 0)
        self.assertEqual(x2, 599)
        self.assertEqual(y2, 299)

    def test_capture_selector_to(self):
        self.ghost.open(base_url)
        self.ghost.capture_to('test.png', selector='h1')
        self.assertTrue(os.path.isfile('test.png'))
        os.remove('test.png')

    def test_set_field_value_checkbox_true(self):
        self.ghost.open("%sform" % base_url)
        self.ghost.set_field_value('[name=checkbox]', True)
        value, resssources = self.ghost.evaluate(
            'document.getElementById("checkbox").checked')
        self.assertEqual(value, True)

    def test_set_field_value_checkbox_false(self):
        self.ghost.open("%sform" % base_url)
        self.ghost.set_field_value('[name=checkbox]', False)
        value, resssources = self.ghost.evaluate(
            'document.getElementById("checkbox").checked')
        self.assertEqual(value, False)

    def test_set_field_value_checkbox_multiple(self):
        self.ghost.open("%sform" % base_url)
        self.ghost.set_field_value('[name=multiple-checkbox]',
            'second choice')
        value, resources = self.ghost.evaluate(
            'document.getElementById("multiple-checkbox-first").checked')
        self.assertEqual(value, False)
        value, resources = self.ghost.evaluate(
            'document.getElementById("multiple-checkbox-second").checked')
        self.assertEqual(value, True)

    def test_set_field_value_email(self):
        expected = 'my@awesome.email'
        self.ghost.open("%sform" % base_url)
        self.ghost.set_field_value('[name=email]', expected)
        value, resssources = self.ghost\
            .evaluate('document.getElementById("email").value')
        self.assertEqual(value, expected)

    def test_set_field_value_text(self):
        expected = 'sample text'
        self.ghost.open("%sform" % base_url)
        self.ghost.set_field_value('[name=text]', expected)
        value, resssources = self.ghost\
            .evaluate('document.getElementById("text").value')
        self.assertEqual(value, expected)

    def test_set_field_value_radio(self):
        self.ghost.open("%sform" % base_url)
        self.ghost.set_field_value('[name=radio]',
            'first choice')
        value, resources = self.ghost.evaluate(
            'document.getElementById("radio-first").checked')
        self.assertEqual(value, True)
        value, resources = self.ghost.evaluate(
            'document.getElementById("radio-second").checked')
        self.assertEqual(value, False)

    def test_set_field_value_textarea(self):
        expected = 'sample text\nanother line'
        self.ghost.open("%sform" % base_url)
        self.ghost.set_field_value('[name=textarea]', expected)
        value, resssources = self.ghost\
            .evaluate('document.getElementById("textarea").value')
        self.assertEqual(value, expected)

    def test_set_field_value_select(self):
        self.ghost.open("%sform" % base_url)
        self.ghost.set_field_value('[name=selectbox]', 'two')
        value, resources = self.ghost.evaluate(
            "document.querySelector('option[value=two]').selected;")
        self.assertTrue(value)
        value, resources = self.ghost.evaluate(
            "document.querySelector('option[value=one]').selected;")
        self.assertFalse(value)

    def test_set_field_value_simple_file_field(self):
        self.ghost.open("%supload" % base_url)
        self.ghost.set_field_value('[name=simple-file]',
            os.path.join(os.path.dirname(__file__), 'static', 'blackhat.jpg'))
        page, resources = self.ghost.call('form', 'submit',
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
        file_path = os.path.join(os.path.dirname(__file__), 'static', 'foo.tar.gz')
        if PY3:
            f = open(file_path, 'r', encoding='latin-1')
        else:
            f = open(file_path, 'r')
        foo = f.read(1024)
        f.close()

        self.assertEqual(resources[0].content, foo)

    def test_url_with_hash(self):
        page, resources = self.ghost.open("%surl-hash" % base_url)
        self.assertIsNotNone(page)
        self.assertTrue("Test page" in self.ghost.content)

    def test_url_with_hash_header(self):
        page, resources = self.ghost.open("%surl-hash-header" % base_url)
        self.assertIsNotNone(page)
        self.assertTrue("Welcome" in self.ghost.content)

    def test_many_assets(self):
        page, resources = self.ghost.open("%smany-assets" % base_url)
        page, resources = self.ghost.open("%smany-assets" % base_url)


if __name__ == '__main__':
    unittest.main()
