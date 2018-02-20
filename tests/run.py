#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import

import io
import json
import logging
import os
import sys
import unittest

from ghost import GhostTestCase
from ghost.bindings import BINDING_NAME
from ghost.ghost import default_user_agent

from .app import app

try:
    import cookielib
except ImportError:
    from http import cookiejar as cookielib


PORT = 5000

base_url = 'http://localhost:%s/' % PORT


class GhostTest(GhostTestCase):
    port = PORT
    display = False

    @classmethod
    def create_app(cls):
        return app

    def test_open(self):
        page, resources = self.session.open(base_url)
        self.assertEqual(page.url, base_url)
        self.assertTrue("Ghost.py" in self.session.content)

    def test_open_page_with_no_cache_headers(self):
        page, resources = self.session.open("%sno-cache" % base_url)
        self.assertIsNotNone(page.content)
        self.assertIn("cache for me", page.content)

    def test_open_403(self):
        page, resources = self.session.open("%sprotected" % base_url)
        self.assertEqual(resources[0].http_status, 403)

    def test_open_404(self):
        page, resources = self.session.open("%s404" % base_url)
        self.assertEqual(page.http_status, 404)

    def test_evaluate(self):
        self.session.open(base_url)
        self.assertEqual(self.session.evaluate("x='ghost'; x;")[0], 'ghost')

    def test_extra_resource_content(self):
        page, resources = self.session.open(base_url)
        self.assertEqual(len(resources), 6)

        for resource in resources:
            if resource.url.endswith('app.js'):
                break
        else:
            raise AssertionError('app.js was not downloaded')

        self.assertIn(b'globals alert', resource.content)

    def test_extra_resource_binaries(self):
        page, resources = self.session.open(base_url)
        self.assertEqual(len(resources), 6)

        for resource in resources:
            if resource.url.endswith('blackhat.jpg'):
                break
        else:
            raise AssertionError('blackhat.jpg was not downloaded')

        self.assertIsInstance(resource.content, bytes)

    def test_wait_for_selector(self):
        page, resources = self.session.open(base_url)
        success, resources = self.session.click("#update-list-button")
        success, resources = self.session\
            .wait_for_selector("#list li:nth-child(2)")
        self.assertEqual(resources[0].url, "%sitems.json" % base_url)

    def test_sleep(self):
        page, resources = self.session.open("%s" % base_url)
        result, _ = self.session.evaluate("window.result")
        self.assertEqual(result, False)
        self.session.sleep(4)
        result, _ = self.session.evaluate("window.result")
        self.assertEqual(result, True)

    def test_wait_for_text(self):
        page, resources = self.session.open(base_url)
        self.session.click("#update-list-button")
        success, resources = self.session.wait_for_text("second item")

    def test_wait_for_timeout(self):
        self.session.open("%s" % base_url)
        self.assertRaises(Exception, self.session.wait_for_text, "undefined")

    def test_fill(self):
        self.session.open(base_url)
        values = {
            'text': 'Here is a sample text.',
            'email': 'my@awesome.email',
            'textarea': 'Here is a sample text.\nWith several lines.',
            'checkbox': True,
            'select': 'two',
            "radio": "first choice"
        }
        self.session.fill('form', values)
        for field in ['text', 'email', 'textarea']:
            value, resssources = self.session\
                .evaluate('document.getElementById("%s").value' % field)
            self.assertEqual(value, values[field])
        value, resources = self.session.evaluate(
            'document.getElementById("checkbox").checked')
        self.assertEqual(value, True)
        value, resources = self.session.evaluate(
            "document.querySelector('option[value=two]').selected;")
        self.assertTrue(value)
        value, resources = self.session.evaluate(
            'document.getElementById("radio-first").checked')
        self.assertEqual(value, True)
        value, resources = self.session.evaluate(
            'document.getElementById("radio-second").checked')
        self.assertEqual(value, False)

    def test_form_submission(self):
        self.session.open(base_url)
        values = {
            'text': 'Here is a sample text.',
        }
        self.session.fill('form', values)
        page, resources = self.session.call(
            'form',
            'submit',
            expect_loading=True,
        )
        self.assertIn('Form successfully sent.', self.session.content)

    def test_global_exists(self):
        self.session.open("%s" % base_url)
        self.assertTrue(self.session.global_exists('myGlobal'))

    def test_resource_headers(self):
        page, resources = self.session.open(base_url)
        self.assertEqual(
            page.headers['Content-Type'],
            'text/html; charset=utf-8',
        )

    def test_click_link(self):
        page, resources = self.session.open(base_url)
        page, resources = self.session.click('a', expect_loading=True)
        self.assertEqual(page.url, "%secho/link" % base_url)

    def test_cookies(self):
        self.session.open("%scookie" % base_url)
        self.assertEqual(len(self.session.cookies), 1)

    def test_delete_cookies(self):
        self.session.open("%scookie" % base_url)
        self.session.delete_cookies()
        self.assertEqual(len(self.session.cookies), 0)

    def test_save_load_cookies(self):
        self.session.delete_cookies()
        self.session.open("%sset/cookie" % base_url)
        self.session.save_cookies('testcookie.txt')
        self.session.delete_cookies()
        self.session.load_cookies('testcookie.txt')
        self.session.open("%sget/cookie" % base_url)
        self.assertTrue('OK' in self.session.content)

    def test_load_cookies_expire_is_none(self):
        self.session.delete_cookies()
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
        self.session.load_cookies(jar)

    def test_wait_for_alert(self):
        self.session.open(base_url)
        self.session.click('#alert-button')
        msg, resources = self.session.wait_for_alert()
        self.assertEqual(msg, 'this is an alert')

    def test_confirm(self):
        self.session.open(base_url)
        with self.session.confirm():
            self.session.click('#confirm-button')
        msg, resources = self.session.wait_for_alert()
        self.assertEqual(msg, 'you confirmed!')

    def test_no_confirm(self):
        self.session.open(base_url)
        with self.session.confirm(False):
            self.session.click('#confirm-button')
        msg, resources = self.session.wait_for_alert()
        self.assertEqual(msg, 'you denied!')

    def test_confirm_callable(self):
        self.session.open(base_url)
        with self.session.confirm(lambda: False):
            self.session.click('#confirm-button')
        msg, resources = self.session.wait_for_alert()
        self.assertEqual(msg, 'you denied!')

    @unittest.skipIf(os.environ.get('TRAVIS') == "true" and
                     os.environ.get('TOXENV') in ("py34-pyqt4", "py34-pyqt5"),
                     'Test broken in this configuration on Travis CI')
    def test_prompt(self):
        self.session.open(base_url)
        with self.session.prompt('my value'):
            self.session.click('#prompt-button')
        value, resources = self.session.evaluate('promptValue')
        self.assertEqual(value, 'my value')

    @unittest.skipIf(os.environ.get('TRAVIS') == "true" and
                     os.environ.get('TOXENV') in ("py34-pyqt4", "py34-pyqt5"),
                     'Test broken in this configuration on Travis CI')
    def test_prompt_callable(self):
        self.session.open(base_url)
        with self.session.prompt(lambda: 'another value'):
            self.session.click('#prompt-button')
        value, resources = self.session.evaluate('promptValue')
        self.assertEqual(value, 'another value')

    @unittest.skipIf(os.environ.get('TRAVIS') == "true" and
                     os.environ.get('TOXENV') == "py34-pyqt4",
                     'Running on Travis CI/Python 3.4/PyQt4')
    def test_popup_messages_collection(self):
        self.session.open(base_url, default_popup_response=True)
        self.session.click('#confirm-button')
        self.assertIn('this is a confirm', self.session.popup_messages)
        self.session.click('#prompt-button')
        self.assertIn('Prompt ?', self.session.popup_messages)
        self.session.click('#alert-button')
        self.assertIn('this is an alert', self.session.popup_messages)

    def test_prompt_default_value_true(self):
        self.session.open(base_url, default_popup_response=True)
        self.session.click('#confirm-button')
        msg, resources = self.session.wait_for_alert()
        self.assertEqual(msg, 'you confirmed!')

    def test_prompt_default_value_false(self):
        self.session.open(base_url, default_popup_response=False)
        self.session.click('#confirm-button')
        msg, resources = self.session.wait_for_alert()
        self.assertEqual(msg, 'you denied!')

    def test_capture_to(self):
        self.session.open(base_url)
        self.session.capture_to('test.png')
        self.assertTrue(os.path.isfile('test.png'))
        os.remove('test.png')

    def test_region_for_selector(self):
        self.session.open(base_url)
        x1, y1, x2, y2 = self.session.region_for_selector('h1')
        self.assertEqual(x1, 30)
        self.assertEqual(y1, 20)
        self.assertEqual(x2, 329)
        self.assertEqual(y2, 59)

    def test_capture_selector_to(self):
        self.session.open(base_url)
        self.session.capture_to('test.png', selector='h1')
        self.assertTrue(os.path.isfile('test.png'))
        os.remove('test.png')

    def test_set_field_value_checkbox_true(self):
        self.session.open(base_url)
        self.session.set_field_value('[name=checkbox]', True)
        value, resssources = self.session.evaluate(
            'document.getElementById("checkbox").checked')
        self.assertEqual(value, True)

    def test_set_field_value_checkbox_false(self):
        self.session.open(base_url)
        self.session.set_field_value('[name=checkbox]', False)
        value, resssources = self.session.evaluate(
            'document.getElementById("checkbox").checked')
        self.assertEqual(value, False)

    def test_set_field_value_checkbox_multiple(self):
        self.session.open(base_url)
        self.session.set_field_value(
            '[name=multiple-checkbox]',
            'second choice',
        )
        value, resources = self.session.evaluate(
            'document.getElementById("multiple-checkbox-first").checked')
        self.assertEqual(value, False)
        value, resources = self.session.evaluate(
            'document.getElementById("multiple-checkbox-second").checked')
        self.assertEqual(value, True)

    def test_set_field_value_email(self):
        expected = 'my@awesome.email'
        self.session.open(base_url)
        self.session.set_field_value('[name=email]', expected)
        value, resssources = self.session\
            .evaluate('document.getElementById("email").value')
        self.assertEqual(value, expected)

    def test_set_field_value_text(self):
        expected = 'sample text'
        self.session.open(base_url)
        self.session.set_field_value('[name=text]', expected)
        value, resssources = self.session\
            .evaluate('document.getElementById("text").value')
        self.assertEqual(value, expected)

    def test_set_field_value_radio(self):
        self.session.open(base_url)
        self.session.set_field_value('[name=radio]', 'first choice')
        value, resources = self.session.evaluate(
            'document.getElementById("radio-first").checked')
        self.assertEqual(value, True)
        value, resources = self.session.evaluate(
            'document.getElementById("radio-second").checked')
        self.assertEqual(value, False)

    def test_set_field_value_textarea(self):
        expected = 'sample text\nanother line'
        self.session.open(base_url)
        self.session.set_field_value('[name=textarea]', expected)
        value, resssources = self.session\
            .evaluate('document.getElementById("textarea").value')
        self.assertEqual(value, expected)

    def test_set_field_value_select(self):
        self.session.open(base_url)
        self.session.set_field_value('[name=select]', 'two')
        value, resources = self.session.evaluate(
            "document.querySelector('option[value=two]').selected;")
        self.assertTrue(value)
        value, resources = self.session.evaluate(
            "document.querySelector('option[value=one]').selected;")
        self.assertFalse(value)

    @unittest.skipIf(
        BINDING_NAME == 'PyQt5' or
        os.environ.get('TRAVIS') == "true",
        'Running on Travis CI or using PyQt5'
    )
    def test_set_field_value_simple_file_field(self):
        self.session.open(base_url)
        self.session.set_field_value(
            '[name=simple-file]',
            os.path.join(os.path.dirname(__file__), 'static', 'blackhat.jpg'),
        )
        page, resources = self.session.call(
            'form',
            'submit',
            expect_loading=True,
        )
        file_path = os.path.join(os.path.dirname(__file__),
                                 'uploaded_blackhat.jpg')

        try:
            self.assertTrue(os.path.isfile(file_path),
                            msg='QtWebKit did not provide local file name')
            os.remove(file_path)
        except AssertionError:
            os.remove(os.path.join(os.path.dirname(__file__), 'uploaded_'))
            raise

    def test_basic_http_auth_success(self):
        page, resources = self.session.open(
            "%sbasic-auth" % base_url,
            auth=('admin', 'secret'),
        )
        self.assertEqual(page.http_status, 200)

    def test_basic_http_auth_error(self):
        page, resources = self.session.open(
            "%sbasic-auth" % base_url,
            auth=('admin', 'wrongsecret'),
        )
        self.assertEqual(page.http_status, 401)

    def test_unsupported_content(self):
        page, resources = self.session.open("%ssend-file" % base_url)
        file_path = os.path.join(
            os.path.dirname(__file__),
            'static',
            'foo.tar.gz',
        )
        with io.open(file_path, 'rb') as f:
            foo = f.read()

        self.assertEqual(resources[0].content, foo)

    def test_url_with_hash(self):
        page, resources = self.session.open(base_url)
        self.session.evaluate('document.location.hash = "test";')
        self.assertIsNotNone(page)
        self.assertTrue("Ghost.py" in self.session.content)

    def test_url_with_hash_header(self):
        page, resources = self.session.open("%surl-hash-header" % base_url)
        self.assertIsNotNone(page)
        self.assertTrue("Welcome" in self.session.content)

    def test_many_assets(self):
        page, resources = self.session.open("%smany-assets" % base_url)
        page, resources = self.session.open("%smany-assets" % base_url)

    def test_frame_ascend(self):
        session = self.session
        session.open(base_url)
        session.frame('first-frame')
        self.assertIn('frame 1', session.content)
        self.assertNotIn('Ghost.py', session.content)
        session.frame()
        self.assertNotIn('frame 1', session.content)
        self.assertIn('Ghost.py', session.content)

    def test_frame_descend_by_name(self):
        session = self.session
        session.open(base_url)
        self.assertNotIn('frame 1', session.content)
        session.frame('first-frame')
        self.assertIn('frame 1', session.content)

    def test_frame_descend_by_name_invalid(self):
        session = self.session
        session.open(base_url)
        self.assertRaises(LookupError, session.frame, 'third-frame')

    def test_frame_descend_by_index(self):
        session = self.session
        session.open(base_url)
        self.assertNotIn('frame 2', session.content)
        session.frame(1)
        self.assertIn('frame 2', session.content)

    def test_frame_descend_by_index_invalid(self):
        session = self.session
        session.open(base_url)
        self.assertRaises(LookupError, session.frame, 10)

    def test_set_user_agent(self):
        def get_user_agent(session, **kwargs):
            page, resources = self.session.open(
                "%sdump" % base_url,
                **kwargs
            )
            data = json.loads(page.content.decode('utf-8'))
            return data['headers']['User-Agent']

        session = self.session

        self.assertEqual(get_user_agent(session), default_user_agent)

        new_agent = 'New Agent'

        self.assertEqual(
            get_user_agent(session, user_agent=new_agent),
            new_agent,
        )

    def test_exclude_regex(self):
        session = self.ghost.start(exclude="\.(jpg|css)")
        page, resources = session.open(base_url)
        url_loaded = [r.url for r in resources]
        self.assertFalse(
            "%sstatic/styles.css" % base_url in url_loaded)
        self.assertFalse(
            "%sstatic/blackhat.jpg" % base_url in url_loaded)
        session.exit()

if __name__ == '__main__':
    unittest.main()
