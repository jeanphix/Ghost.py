# -*- coding: utf-8 -*-
import os
import time
import codecs
import json
import logging
import subprocess
from functools import wraps
try:
    from PyQt4 import QtWebKit
    from PyQt4.QtNetwork import QNetworkRequest, QNetworkAccessManager,\
                                QNetworkCookieJar
    from PyQt4.QtCore import QSize, QByteArray, QUrl
    from PyQt4.QtGui import QApplication, QImage, QPainter
except ImportError:
    raise Exception("Ghost.py requires PyQt")


default_user_agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/535.2 " +\
    "(KHTML, like Gecko) Chrome/15.0.874.121 Safari/535.2"


logger = logging.getLogger('ghost')


class Logger(logging.Logger):
    @staticmethod
    def log(message, sender="Ghost", level="info"):
        if not hasattr(logger, level):
            raise Exception('invalid log level')
        getattr(logger, level)("%s: %s", sender, message)


class GhostWebPage(QtWebKit.QWebPage):
    """Overrides QtWebKit.QWebPage in order to intercept some graphical
    behaviours like alert(), confirm().
    Also intercepts client side console.log().
    """
    def chooseFile(self, frame, suggested_file=None):
        return Ghost._upload_file

    def javaScriptConsoleMessage(self, message, *args, **kwargs):
        """Prints client console message in current output stream."""
        super(GhostWebPage, self).javaScriptConsoleMessage(message, *args,
        **kwargs)
        log_type = "error" if "Error" in message else "info"
        Logger.log(message, sender="Frame", level=log_type)

    def javaScriptAlert(self, frame, message):
        """Notifies ghost for alert, then pass."""
        Ghost._alert = message
        Logger.log("alert('%s')" % message, sender="Frame")

    def javaScriptConfirm(self, frame, message):
        """Checks if ghost is waiting for confirm, then returns the right
        value.
        """
        if Ghost._confirm_expected is None:
            raise Exception('You must specified a value to confirm "%s"' %
                message)
        confirmation, callback = Ghost._confirm_expected
        Ghost._confirm_expected = None
        Logger.log("confirm('%s')" % message, sender="Frame")
        if callback is not None:
            return callback()
        return confirmation

    def javaScriptPrompt(self, frame, message, defaultValue, result):
        """Checks if ghost is waiting for prompt, then enters the right
        value.
        """
        if Ghost._prompt_expected is None:
            raise Exception('You must specified a value for prompt "%s"' %
                message)
        result_value, callback = Ghost._prompt_expected
        Logger.log("prompt('%s')" % message, sender="Frame")
        if callback is not None:
            result_value = callback()
        result.append(result_value)
        if result_value == '':
            Logger.log("'%s' prompt filled with empty string" % message,
                level='warning')
        Ghost._prompt_expected = None
        return True


def can_load_page(func):
    """Decorator that specifies if user can expect page loading from
    this action. If expect_loading is set to True, ghost will wait
    for page_loaded event.
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if 'expect_loading' in kwargs:
            expect_loading = True
            del kwargs['expect_loading']
        else:
            expect_loading = False
        if expect_loading:
            self.loaded = False
            func(self, *args, **kwargs)
            return self.wait_for_page_loaded()
        return func(self, *args, **kwargs)
    return wrapper


def client_utils_required(func):
    """Decorator that checks avabality of Ghost client side utils,
    injects require javascript file instead.
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if not self.global_exists('GhostUtils'):
            self.evaluate_js_file(
                os.path.join(os.path.dirname(__file__), 'utils.js'))
        return func(self, *args, **kwargs)
    return wrapper


class HttpRessource(object):
    """Represents an HTTP ressource.
    """
    def __init__(self, reply):
        self.url = unicode(reply.url().toString())
        self.http_status = reply.attribute(
            QNetworkRequest.HttpStatusCodeAttribute).toInt()[0]
        self.headers = {}
        for header in reply.rawHeaderList():
            self.headers[unicode(header)] = unicode(reply.rawHeader(header))
        self._reply = reply


class Ghost(object):
    """Ghost manages a QWebPage.

    :param user_agent: The default User-Agent header.
    :param wait_timeout: Maximum step duration in second.
    :param wait_callback: An optional callable that is periodically
        executed until Ghost stops waiting.
    :param log_level: The optional logging level.
    :param display: A boolean that tells ghost to displays UI.
    """
    _alert = None
    _confirm_expected = None
    _prompt_expected = None
    _upload_file = None

    def __init__(self, user_agent=default_user_agent, wait_timeout=8,
            wait_callback=None, log_level=logging.WARNING, display=False):
        self.http_ressources = []

        self.user_agent = user_agent
        self.wait_timeout = wait_timeout
        self.wait_callback = wait_callback

        self.loaded = True

        if not 'DISPLAY' in os.environ and not hasattr(Ghost, 'xvfb'):
            try:
                os.environ['DISPLAY'] = ':99'
                Ghost.xvfb = subprocess.Popen(['Xvfb', ':99'])
            except OSError:
                raise Exception('Xvfb is required to a ghost run oustside ' +\
                    'an X instance')

        self.display = display

        self.app = QApplication(['ghost'])

        self.page = GhostWebPage(self.app)
        self.set_viewport_size(400, 300)

        self.page.loadFinished.connect(self._page_loaded)
        self.page.loadStarted.connect(self._page_load_started)

        self.manager = self.page.networkAccessManager()
        self.manager.finished.connect(self._request_ended)

        self.cookie_jar = QNetworkCookieJar()
        self.manager.setCookieJar(self.cookie_jar)

        self.main_frame = self.page.mainFrame()

        logger.setLevel(log_level)

        if self.display:
            self.webview = QtWebKit.QWebView()
            self.webview.setPage(self.page)
            self.webview.show()

    def __del__(self):
        self.exit()

    def capture(self, region=None, selector=None, format=QImage.Format_ARGB32):
        """Returns snapshot as QImage.

        :param region: An optional tupple containing region as pixel
            coodinates.
        :param selector: A selector targeted the element to crop on.
        :param format: The output image format.
        """
        if region is None and selector is not None:
            region = self.region_for_selector(selector)
        if region:
            x1, y1, x2, y2 = region
            w, h = (x2 - x1), (y2 - y1)
            image = QImage(QSize(x2, y2), format)
            painter = QPainter(image)
            self.main_frame.render(painter)
            painter.end()
            image = image.copy(x1, y1, w, h)
        else:
            image = QImage(self.page.viewportSize(), format)
            painter = QPainter(image)
            self.main_frame.render(painter)
            painter.end()
        return image

    def capture_to(self, path, region=None, selector=None,
        format=QImage.Format_ARGB32):
        """Saves snapshot as image.

        :param path: The destination path.
        :param region: An optional tupple containing region as pixel
            coodinates.
        :param selector: A selector targeted the element to crop on.
        :param format: The output image format.
        """
        self.capture(region=region, format=format,
            selector=selector).save(path)

    @client_utils_required
    @can_load_page
    def click(self, selector):
        """Click the targeted element.

        :param selector: A CSS3 selector to targeted element.
        """
        if not self.exists(selector):
            raise Exception("Can't find element to click")
        return self.evaluate('GhostUtils.click("%s");' % selector)

    class confirm:
        """Statement that tells Ghost how to deal with javascript confirm().

        :param confirm: A bollean that confirm.
        :param callable: A callable that returns a boolean for confirmation.
        """
        def __init__(self, confirm=True, callback=None):
            self.confirm = confirm
            self.callback = callback

        def __enter__(self):
            Ghost._confirm_expected = (self.confirm, self.callback)

        def __exit__(self, type, value, traceback):
            Ghost._confirm_expected = None

    @property
    def content(self):
        """Returns current frame HTML as a string."""
        return unicode(self.main_frame.toHtml())

    @property
    def cookies(self):
        """Returns all cookies."""
        return self.cookie_jar.allCookies()

    def delete_cookies(self):
        """Deletes all cookies."""
        self.cookie_jar.setAllCookies([])

    @can_load_page
    def evaluate(self, script):
        """Evaluates script in page frame.

        :param script: The script to evaluate.
        """
        return (self.main_frame.evaluateJavaScript("%s" % script),
            self._release_last_ressources())

    def evaluate_js_file(self, path, encoding='utf-8'):
        """Evaluates javascript file at given path in current frame.
        Raises native IOException in case of invalid file.

        :param path: The path of the file.
        :param encoding: The file's encoding.
        """
        self.evaluate(codecs.open(path, encoding=encoding).read())

    def exists(self, selector):
        """Checks if element exists for given selector.

        :param string: The element selector.
        """
        return not self.main_frame.findFirstElement(selector).isNull()

    def exit(self):
        """Exits application and relateds."""
        if self.display:
            self.webview.close()
        self.app.exit()
        del self.manager
        del self.page
        del self.main_frame
        del self.app
        if hasattr(self, 'xvfb'):
            self.xvfb.terminate()

    @can_load_page
    def fill(self, selector, values):
        """Fills a form with provided values.

        :param selector: A CSS selector to the target form to fill.
        :param values: A dict containing the values.
        """
        if not self.exists(selector):
            raise Exception("Can't find form")
        ressources = []
        for field in values:
            r, res = self.set_field_value("%s [name=%s]" % (selector, field),
                values[field])
            ressources.extend(res)
        return True, ressources

    @client_utils_required
    @can_load_page
    def fire_on(self, selector, method):
        """Call method on element matching given selector.

        :param selector: A CSS selector to the target element.
        :param method: The name of the method to fire.
        :param expect_loading: Specifies if a page loading is expected.
        """
        return self.evaluate('GhostUtils.fireOn("%s", "%s");' % (
            selector, method))

    def global_exists(self, global_name):
        """Checks if javascript global exists.

        :param global_name: The name of the global.
        """
        return self.evaluate('!(typeof %s === "undefined");' %
            global_name)[0].toBool()

    def hide(self):
        """Close the webview."""
        try:
            self.webview.close()
        except:
            raise Exception("no webview to close")

    def open(self, address, method='get'):
        """Opens a web page.

        :param address: The ressource URL.
        :param method: The Http method.
        :return: Page ressource, All loaded ressources.
        """
        body = QByteArray()
        try:
            method = getattr(QNetworkAccessManager,
                "%sOperation" % method.capitalize())
        except AttributeError:
            raise Exception("Invalid http method %s" % method)
        request = QNetworkRequest(QUrl(address))
        request.setRawHeader("User-Agent", self.user_agent)
        self.main_frame.load(request, method, body)
        self.loaded = False
        return self.wait_for_page_loaded()

    class prompt:
        """Statement that tells Ghost how to deal with javascript prompt().

        :param value: A string value to fill in prompt.
        :param callback: A callable that returns the value to fill in.
        """
        def __init__(self, value='', callback=None):
            self.value = value
            self.callback = callback

        def __enter__(self):
            Ghost._prompt_expected = (self.value, self.callback)

        def __exit__(self, type, value, traceback):
            Ghost._prompt_expected = None

    @client_utils_required
    def region_for_selector(self, selector):
        """Returns frame region for given selector as tupple.

        :param selector: The targeted element.
        """
        geo = self.main_frame.findFirstElement(selector).geometry()
        try:
            region = (geo.left(), geo.top(), geo.right(), geo.bottom())
        except:
            raise Exception("can't get region for selector '%s'" % selector)
        return region

    @can_load_page
    @client_utils_required
    def set_field_value(self, selector, value, blur=True):
        """Sets the value of the field matched by given selector.

        :param selector: A CSS selector that target the field.
        :param value: The value to fill in.
        :param blur: An optional boolean that force blur when filled in.
        """
        def _set_text_value(selector, value):
            return self.evaluate(
                'document.querySelector("%s").value=%s;' %
                    (selector, json.dumps(value)))

        res, ressources = None, []

        element = self.main_frame.findFirstElement(selector)
        if element.isNull():
            raise Exception('can\'t find element for %s"' % selector)
        self.fire_on(selector, 'focus')
        if element.tagName() in ["TEXTAREA", "SELECT"]:
            res, ressources = _set_text_value(selector, value)
        elif element.tagName() == "INPUT":
            if element.attribute('type') in ["color", "date", "datetime",
                "datetime-local", "email", "hidden", "month", "number",
                "password", "range", "search", "tel", "text", "time",
                "url", "week"]:
                res, ressources = _set_text_value(selector, value)
            elif element.attribute('type') == "checkbox":
                res, ressources = self.evaluate(
                    'GhostUtils.setCheckboxValue("%s", %s);' %
                        (selector, json.dumps(value)))
            elif element.attribute('type') == "radio":
                res, ressources = self.evaluate(
                    'GhostUtils.setRadioValue("%s", %s);' %
                        (selector, json.dumps(value)))
            elif element.attribute('type') == "file":
                Ghost._upload_file = value
                res, ressources = self.click(selector)
                Ghost._upload_file = None
        else:
            raise Exception('unsuported field tag')
        if blur:
            self.fire_on(selector, 'blur')
        return res, ressources

    def set_viewport_size(self, width, height):
        """Sets the page viewport size.

        :param width: An integer that sets width pixel count.
        :param height: An integer that sets height pixel count.
        """
        self.page.setViewportSize(QSize(width, height))

    def show(self):
        """Show current page inside a QWebView.
        """
        self.webview = QtWebKit.QWebView()
        self.webview.setPage(self.page)
        self.webview.show()

    def wait_for_alert(self):
        """Waits for main frame alert().
        """
        self._wait_for(lambda: Ghost._alert is not None,
            'User has not been alerted.')
        msg = Ghost._alert
        Ghost._alert = None
        return msg, self._release_last_ressources()

    def wait_for_page_loaded(self):
        """Waits until page is loaded, assumed that a page as been requested.
        """
        self._wait_for(lambda: self.loaded,
            'Unable to load requested page')
        ressources = self._release_last_ressources()
        page = None
        for ressource in ressources:
            if not int(ressource.http_status / 100) == 3:
                # Assumed that current ressource is the first non redirect
                page = ressource
        return page, ressources

    def wait_for_selector(self, selector):
        """Waits until selector match an element on the frame.

        :param selector: The selector to wait for.
        """
        self._wait_for(lambda: self.exists(selector),
            'Can\'t find element matching "%s"' % selector)
        return True, self._release_last_ressources()

    def wait_for_text(self, text):
        """Waits until given text appear on main frame.

        :param text: The text to wait for.
        """
        self._wait_for(lambda: text in self.content,
            'Can\'t find "%s" in current frame' % text)
        return True, self._release_last_ressources()

    def _release_last_ressources(self):
        """Releases last loaded ressources.

        :return: The released ressources.
        """
        last_ressources = self.http_ressources
        self.http_ressources = []
        return last_ressources

    def _page_loaded(self):
        """Called back when page is loaded.
        """
        self.loaded = True

    def _page_load_started(self):
        """Called back when page load started.
        """
        self.loaded = False

    def _request_ended(self, res):
        """Adds an HttpRessource object to http_ressources.

        :param res: The request result.
        """
        self.http_ressources.append(HttpRessource(res))

    def _wait_for(self, condition, timeout_message):
        """Waits until condition is True.

        :param condition: A callable that returns the condition.
        :param timeout_message: The exception message on timeout.
        """
        started_at = time.time()
        while not condition():
            if time.time() > (started_at + self.wait_timeout):
                raise Exception(timeout_message)
            time.sleep(0.01)
            self.app.processEvents()
            if self.wait_callback is not None:
                self.wait_callback()
