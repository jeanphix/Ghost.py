# -*- coding: utf-8 -*-
import sys
import os
import time
import codecs
import logging
import subprocess
import tempfile
from functools import wraps
from cookielib import Cookie, LWPCookieJar


bindings = ["PySide", "PyQt4"]

binding = None
for name in bindings:
    try:
        binding = __import__(name)
        break
    except ImportError:
        continue


if not binding:
    raise Exception("Ghost.py requires PySide or PyQt4")


PYSIDE = binding.__name__ == 'PySide'

if not PYSIDE:
    import sip
    sip.setapi('QVariant', 2)


def _import(name):
    name = "%s.%s" % (binding.__name__, name)
    module = __import__(name)
    for n in name.split(".")[1:]:
        module = getattr(module, n)
    return module


QtCore = _import("QtCore")
QSize = QtCore.QSize
QByteArray = QtCore.QByteArray
QUrl = QtCore.QUrl
QDateTime = QtCore.QDateTime
QtCriticalMsg = QtCore.QtCriticalMsg
QtDebugMsg = QtCore.QtDebugMsg
QtFatalMsg = QtCore.QtFatalMsg
QtWarningMsg = QtCore.QtWarningMsg
qInstallMsgHandler = QtCore.qInstallMsgHandler

QtGui = _import("QtGui")
QApplication = QtGui.QApplication
QImage = QtGui.QImage
QPainter = QtGui.QPainter
QPrinter = QtGui.QPrinter

QtNetwork = _import("QtNetwork")
QNetworkRequest = QtNetwork.QNetworkRequest
QNetworkAccessManager = QtNetwork.QNetworkAccessManager
QNetworkCookieJar = QtNetwork.QNetworkCookieJar
QNetworkDiskCache = QtNetwork.QNetworkDiskCache
QNetworkProxy = QtNetwork.QNetworkProxy
QNetworkCookie = QtNetwork.QNetworkCookie

QtWebKit = _import('QtWebKit')


default_user_agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/535.2 " +\
    "(KHTML, like Gecko) Chrome/15.0.874.121 Safari/535.2"


logger = logging.getLogger('ghost')


class Error(Exception):
    """Base class for Ghost exceptions."""
    pass


class TimeoutError(Error):
    """Raised when a request times out"""
    pass


class Logger(logging.Logger):
    @staticmethod
    def log(message, sender="Ghost", level="info"):
        if not hasattr(logger, level):
            raise Error('invalid log level')
        getattr(logger, level)("%s: %s", sender, message)


class QTMessageProxy(object):
    def __init__(self, debug=False):
        self.debug = debug

    def __call__(self, msgType, msg):
        if msgType == QtDebugMsg and self.debug:
            Logger.log(msg, sender='QT', level='debug')
        elif msgType == QtWarningMsg and self.debug:
            Logger.log(msg, sender='QT', level='warning')
        elif msgType == QtCriticalMsg:
            Logger.log(msg, sender='QT', level='critical')
        elif msgType == QtFatalMsg:
            Logger.log(msg, sender='QT', level='fatal')
        elif self.debug:
            Logger.log(msg, sender='QT', level='info')


class GhostWebPage(QtWebKit.QWebPage):
    """Overrides QtWebKit.QWebPage in order to intercept some graphical
    behaviours like alert(), confirm().
    Also intercepts client side console.log().
    """
    def __init__(self, app, ghost):
        self.ghost = ghost
        super(GhostWebPage, self).__init__(app)

    def chooseFile(self, frame, suggested_file=None):
        return Ghost._upload_file

    def javaScriptConsoleMessage(self, message, line, source):
        """Prints client console message in current output stream."""
        super(GhostWebPage, self).javaScriptConsoleMessage(message, line,
            source)
        log_type = "error" if "Error" in message else "info"
        Logger.log("%s(%d): %s" % (source or '<unknown>', line, message),
        sender="Frame", level=log_type)

    def javaScriptAlert(self, frame, message):
        """Notifies ghost for alert, then pass."""
        Ghost._alert = message
        self.ghost.append_popup_message(message)
        Logger.log("alert('%s')" % message, sender="Frame")

    def javaScriptConfirm(self, frame, message):
        """Checks if ghost is waiting for confirm, then returns the right
        value.
        """
        if Ghost._confirm_expected is None:
            raise Error('You must specified a value to confirm "%s"' %
                message)
        self.ghost.append_popup_message(message)
        confirmation, callback = Ghost._confirm_expected
        Logger.log("confirm('%s')" % message, sender="Frame")
        if callback is not None:
            return callback()
        return confirmation

    def javaScriptPrompt(self, frame, message, defaultValue, result=None):
        """Checks if ghost is waiting for prompt, then enters the right
        value.
        """
        if Ghost._prompt_expected is None:
            raise Error('You must specified a value for prompt "%s"' %
                message)
        self.ghost.append_popup_message(message)
        result_value, callback = Ghost._prompt_expected
        Logger.log("prompt('%s')" % message, sender="Frame")
        if callback is not None:
            result_value = callback()
        if result_value == '':
            Logger.log("'%s' prompt filled with empty string" % message,
                level='warning')

        if result is None:
            # PySide
            return True, result_value
        result.append(unicode(result_value))
        return True

    def setUserAgent(self, user_agent):
        self.user_agent = user_agent

    def userAgentForUrl(self, url):
        return self.user_agent


def can_load_page(func):
    """Decorator that specifies if user can expect page loading from
    this action. If expect_loading is set to True, ghost will wait
    for page_loaded event.
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        expect_loading = False
        if 'expect_loading' in kwargs:
            expect_loading = kwargs['expect_loading']
            del kwargs['expect_loading']
        if expect_loading:
            self.loaded = False
            func(self, *args, **kwargs)
            return self.wait_for_page_loaded()
        return func(self, *args, **kwargs)
    return wrapper


class HttpResource(object):
    """Represents an HTTP resource.
    """
    def __init__(self, reply, cache, content=None):
        self.url = reply.url().toString()
        self.content = content
        if cache and self.content is None:
            # Tries to get back content from cache
            buffer = None
            if PYSIDE:
                buffer = cache.data(reply.url().toString())
            else:
                buffer = cache.data(reply.url())
            if buffer is not None:
                content = buffer.readAll()
        try:
            self.content = unicode(content)
        except UnicodeDecodeError:
            self.content = content
        self.http_status = reply.attribute(
            QNetworkRequest.HttpStatusCodeAttribute)
        Logger.log("Resource loaded: %s %s" % (self.url, self.http_status))
        self.headers = {}
        for header in reply.rawHeaderList():
            try:
                self.headers[unicode(header)] = unicode(
                    reply.rawHeader(header))
            except UnicodeDecodeError:
                # it will lose the header value,
                # but at least not crash the whole process
                logger.error(
                    "Invalid characters in header {0}={1}".format(header, reply.rawHeader(header))
                )
        self._reply = reply


class Ghost(object):
    """Ghost manages a QWebPage.

    :param user_agent: The default User-Agent header.
    :param wait_timeout: Maximum step duration in second.
    :param wait_callback: An optional callable that is periodically
        executed until Ghost stops waiting.
    :param log_level: The optional logging level.
    :param display: A boolean that tells ghost to displays UI.
    :param viewport_size: A tuple that sets initial viewport size.
    :param ignore_ssl_errors: A boolean that forces ignore ssl errors.
    :param cache_dir: A directory path where to store cache datas.
    :param plugins_enabled: Enable plugins (like Flash).
    :param java_enabled: Enable Java JRE.
    :param plugin_path: Array with paths to plugin directories
        (default ['/usr/lib/mozilla/plugins'])
    :param download_images: Indicate if the browser should download images
    """
    _alert = None
    _confirm_expected = None
    _prompt_expected = None
    _upload_file = None
    _app = None

    def __init__(self,
            user_agent=default_user_agent,
            wait_timeout=8,
            wait_callback=None,
            log_level=logging.WARNING,
            display=False,
            viewport_size=(800, 600),
            ignore_ssl_errors=True,
            cache_dir=os.path.join(tempfile.gettempdir(), "ghost.py"),
            plugins_enabled=False,
            java_enabled=False,
            plugin_path=['/usr/lib/mozilla/plugins', ],
            download_images=True,
            qt_debug=False,
            show_scrollbars=True,
            network_access_manager_class=None):

        self.http_resources = []

        self.user_agent = user_agent
        self.wait_timeout = wait_timeout
        self.wait_callback = wait_callback
        self.ignore_ssl_errors = ignore_ssl_errors
        self.loaded = True

        if sys.platform.startswith('linux') and not 'DISPLAY' in os.environ\
                and not hasattr(Ghost, 'xvfb'):
            try:
                os.environ['DISPLAY'] = ':99'
                Ghost.xvfb = subprocess.Popen(['Xvfb', ':99'])
            except OSError:
                raise Error('Xvfb is required to a ghost run outside ' +
                            'an X instance')

        self.display = display

        if not Ghost._app:
            Ghost._app = QApplication.instance() or QApplication(['ghost'])
            qInstallMsgHandler(QTMessageProxy(qt_debug))
            if plugin_path:
                for p in plugin_path:
                    Ghost._app.addLibraryPath(p)

        self.popup_messages = []
        self.page = GhostWebPage(Ghost._app, self)

        if network_access_manager_class is not None:
            self.page.setNetworkAccessManager(network_access_manager_class())

        QtWebKit.QWebSettings.setMaximumPagesInCache(0)
        QtWebKit.QWebSettings.setObjectCacheCapacities(0, 0, 0)
        QtWebKit.QWebSettings.globalSettings().setAttribute(
            QtWebKit.QWebSettings.LocalStorageEnabled, True)

        self.page.setForwardUnsupportedContent(True)
        self.page.settings().setAttribute(
            QtWebKit.QWebSettings.AutoLoadImages, download_images)
        self.page.settings().setAttribute(
            QtWebKit.QWebSettings.PluginsEnabled, plugins_enabled)
        self.page.settings().setAttribute(QtWebKit.QWebSettings.JavaEnabled,
            java_enabled)

        if not show_scrollbars:
            self.page.mainFrame().setScrollBarPolicy(QtCore.Qt.Vertical,
                QtCore.Qt.ScrollBarAlwaysOff)
            self.page.mainFrame().setScrollBarPolicy(QtCore.Qt.Horizontal,
                QtCore.Qt.ScrollBarAlwaysOff)

        self.set_viewport_size(*viewport_size)

        # Page signals
        self.page.loadFinished.connect(self._page_loaded)
        self.page.loadStarted.connect(self._page_load_started)
        self.page.unsupportedContent.connect(self._unsupported_content)

        self.manager = self.page.networkAccessManager()
        self.manager.finished.connect(self._request_ended)
        self.manager.sslErrors.connect(self._on_manager_ssl_errors)
        # Cache
        if cache_dir:
            self.cache = QNetworkDiskCache()
            self.cache.setCacheDirectory(cache_dir)
            self.manager.setCache(self.cache)
        else:
            self.cache = None
        # Cookie jar
        self.cookie_jar = QNetworkCookieJar()
        self.manager.setCookieJar(self.cookie_jar)
        # User Agent
        self.page.setUserAgent(self.user_agent)

        self.page.networkAccessManager().authenticationRequired\
            .connect(self._authenticate)
        self.page.networkAccessManager().proxyAuthenticationRequired\
            .connect(self._authenticate)

        self.main_frame = self.page.mainFrame()

        logger.setLevel(log_level)

        class GhostQWebView(QtWebKit.QWebView):
            def sizeHint(self):
                return QSize(*viewport_size)

        self.webview = GhostQWebView()

        if plugins_enabled:
            self.webview.settings().setAttribute(
                QtWebKit.QWebSettings.PluginsEnabled, True)
        if java_enabled:
            self.webview.settings().setAttribute(
                QtWebKit.QWebSettings.JavaEnabled, True)

        self.webview.setPage(self.page)

        if self.display:
            self.webview.show()

    def __del__(self):
        self.exit()

    def ascend_to_root_frame(self):
        """ Set main frame as current main frame's parent.
        """
        # we can't ascend directly to parent frame because it might have been
        # deleted
        self.main_frame = self.page.mainFrame()

    def descend_frame(self, child_name):
        """ Set main frame as one of current main frame's children.

        :param child_name: The name of the child to descend to.
        """
        for frame in self.main_frame.childFrames():
            if frame.frameName() == child_name:
                self.main_frame = frame
                return
        # frame not found so we throw an exception
        raise LookupError("Child frame '%s' not found." % child_name)

    def capture(self, region=None, selector=None,
            format=QImage.Format_ARGB32_Premultiplied):
        """Returns snapshot as QImage.

        :param region: An optional tuple containing region as pixel
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
            self.main_frame.setScrollBarPolicy(QtCore.Qt.Vertical,
                QtCore.Qt.ScrollBarAlwaysOff)
            self.main_frame.setScrollBarPolicy(QtCore.Qt.Horizontal,
                QtCore.Qt.ScrollBarAlwaysOff)
            self.page.setViewportSize(self.main_frame.contentsSize())
            image = QImage(self.page.viewportSize(), format)
            painter = QPainter(image)
            self.main_frame.render(painter)
            painter.end()
        return image

    def capture_to(self, path, region=None, selector=None,
        format=QImage.Format_ARGB32_Premultiplied):
        """Saves snapshot as image.

        :param path: The destination path.
        :param region: An optional tuple containing region as pixel
            coodinates.
        :param selector: A selector targeted the element to crop on.
        :param format: The output image format.
        """
        self.capture(region=region, format=format,
                     selector=selector).save(path)

    def print_to_pdf(self, path, paper_size=(8.5, 11.0),
            paper_margins=(0, 0, 0, 0), paper_units=QPrinter.Inch,
            zoom_factor=1.0):
        """Saves page as a pdf file.

        See qt4 QPrinter documentation for more detailed explanations
        of options.

        :param path: The destination path.
        :param paper_size: A 2-tuple indicating size of page to print to.
        :param paper_margins: A 4-tuple indicating size of each margin.
        :param paper_units: Units for pager_size, pager_margins.
        :param zoom_factor: Scale the output content.
        """
        assert len(paper_size) == 2
        assert len(paper_margins) == 4
        printer = QPrinter(mode=QPrinter.ScreenResolution)
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setPaperSize(QtCore.QSizeF(*paper_size), paper_units)
        printer.setPageMargins(*(paper_margins + (paper_units,)))
        printer.setFullPage(True)
        printer.setOutputFileName(path)
        if self.webview is None:
            self.webview = QtWebKit.QWebView()
            self.webview.setPage(self.page)
        self.webview.setZoomFactor(zoom_factor)
        self.webview.print_(printer)

    @can_load_page
    def click(self, selector):
        """Click the targeted element.

        :param selector: A CSS3 selector to targeted element.
        """
        if not self.exists(selector):
            raise Error("Can't find element to click")
        return self.evaluate("""
            (function () {
                var element = document.querySelector(%s);
                var evt = document.createEvent("MouseEvents");
                evt.initMouseEvent("click", true, true, window, 1, 1, 1, 1, 1,
                    false, false, false, false, 0, element);
                return element.dispatchEvent(evt);
            })();
        """ % repr(selector))

    class confirm:
        """Statement that tells Ghost how to deal with javascript confirm().

        :param confirm: A boolean to set confirmation.
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
    def content(self, to_unicode=True):
        """Returns current frame HTML as a string.

        :param to_unicode: Whether to convert html to unicode or not
        """
        if to_unicode:
            return unicode(self.main_frame.toHtml())
        else:
            return self.main_frame.toHtml()

    @property
    def cookies(self):
        """Returns all cookies."""
        return self.cookie_jar.allCookies()

    def delete_cookies(self):
        """Deletes all cookies."""
        self.cookie_jar.setAllCookies([])

    def clear_alert_message(self):
        """Clears the alert message"""
        self._alert = None

    @can_load_page
    def evaluate(self, script):
        """Evaluates script in page frame.

        :param script: The script to evaluate.
        """
        return (self.main_frame.evaluateJavaScript("%s" % script),
            self._release_last_resources())

    def evaluate_js_file(self, path, encoding='utf-8', **kwargs):
        """Evaluates javascript file at given path in current frame.
        Raises native IOException in case of invalid file.

        :param path: The path of the file.
        :param encoding: The file's encoding.
        """
        with codecs.open(path, encoding=encoding) as f:
            return self.evaluate(f.read(), **kwargs)

    def exists(self, selector):
        """Checks if element exists for given selector.

        :param string: The element selector.
        """
        return not self.main_frame.findFirstElement(selector).isNull()

    def exit(self):
        """Exits application and related."""
        if self.display:
            self.webview.close()
        Ghost._app.quit()
        del self.manager
        del self.page
        del self.main_frame
        if hasattr(self, 'xvfb'):
            self.xvfb.terminate()

    @can_load_page
    def fill(self, selector, values):
        """Fills a form with provided values.

        :param selector: A CSS selector to the target form to fill.
        :param values: A dict containing the values.
        """
        if not self.exists(selector):
            raise Error("Can't find form")
        resources = []
        for field in values:
            r, res = self.set_field_value(
                "%s [name=%s]" % (selector, repr(field)), values[field])
            resources.extend(res)
        return True, resources

    @can_load_page
    def fire_on(self, selector, method):
        """Call method on element matching given selector.

        :param selector: A CSS selector to the target element.
        :param method: The name of the method to fire.
        :param expect_loading: Specifies if a page loading is expected.
        """
        return self.evaluate('document.querySelector(%s)[%s]();' % \
            (repr(selector), repr(method)))

    def global_exists(self, global_name):
        """Checks if javascript global exists.

        :param global_name: The name of the global.
        """
        return self.evaluate('!(typeof this[%s] === "undefined");' %
            repr(global_name))[0]

    def hide(self):
        """Close the webview."""
        try:
            self.webview.close()
        except:
            raise Error("no webview to close")

    def load_cookies(self, cookie_storage, keep_old=False):
        """load from cookielib's CookieJar or Set-Cookie3 format text file.

        :param cookie_storage: file location string on disk or CookieJar
            instance.
        :param keep_old: Don't reset, keep cookies not overridden.
        """
        def toQtCookieJar(PyCookieJar, QtCookieJar):
            allCookies = QtCookieJar.allCookies() if keep_old else []
            for pc in PyCookieJar:
                qc = toQtCookie(pc)
                allCookies.append(qc)
            QtCookieJar.setAllCookies(allCookies)

        def toQtCookie(PyCookie):
            qc = QNetworkCookie(PyCookie.name, PyCookie.value)
            qc.setSecure(PyCookie.secure)
            if PyCookie.path_specified:
                qc.setPath(PyCookie.path)
            if PyCookie.domain != "":
                qc.setDomain(PyCookie.domain)
            if PyCookie.expires and PyCookie.expires != 0:
                t = QDateTime()
                t.setTime_t(PyCookie.expires)
                qc.setExpirationDate(t)
            # not yet handled(maybe less useful):
            #   py cookie.rest / QNetworkCookie.setHttpOnly()
            return qc

        if cookie_storage.__class__.__name__ == 'str':
            cj = LWPCookieJar(cookie_storage)
            cj.load()
            toQtCookieJar(cj, self.cookie_jar)
        elif cookie_storage.__class__.__name__.endswith('CookieJar'):
            toQtCookieJar(cookie_storage, self.cookie_jar)
        else:
            raise ValueError('unsupported cookie_storage type.')

    def open(self, address, method='get', headers={}, auth=None, body=None,
             default_popup_response=None, wait=True):
        """Opens a web page.

        :param address: The resource URL.
        :param method: The Http method.
        :param headers: An optional dict of extra request hearders.
        :param auth: An optional tuple of HTTP auth (username, password).
        :param body: An optional string containing a payload.
        :param default_popup_response: the default response for any confirm/
        alert/prompt popup from the Javascript (replaces the need for the with
        blocks)
        :param wait: If set to True (which is the default), this
        method call waits for the page load to complete before
        returning.  Otherwise, it just starts the page load task and
        it is the caller's responsibilty to wait for the load to
        finish by other means (e.g. by calling wait_for_page_loaded()).
        :return: Page resource, and all loaded resources, unless wait
        is False, in which case it returns None.
        """
        body = body or QByteArray()
        try:
            method = getattr(QNetworkAccessManager,
                             "%sOperation" % method.capitalize())
        except AttributeError:
            raise Error("Invalid http method %s" % method)
        request = QNetworkRequest(QUrl(address))
        request.CacheLoadControl(0)
        for header in headers:
            request.setRawHeader(header, headers[header])
        self._auth = auth
        self._auth_attempt = 0  # Avoids reccursion

        self.main_frame.load(request, method, body)
        self.loaded = False

        if default_popup_response is not None:
            Ghost._prompt_expected = (default_popup_response, None)
            Ghost._confirm_expected = (default_popup_response, None)

        if wait:
            return self.wait_for_page_loaded()

    def scroll_to_anchor(self, anchor):
        self.main_frame.scrollToAnchor(anchor)

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

    def region_for_selector(self, selector):
        """Returns frame region for given selector as tuple.

        :param selector: The targeted element.
        """
        geo = self.main_frame.findFirstElement(selector).geometry()
        try:
            region = (geo.left(), geo.top(), geo.right(), geo.bottom())
        except:
            raise Error("can't get region for selector '%s'" % selector)
        return region

    def save_cookies(self, cookie_storage):
        """Save to cookielib's CookieJar or Set-Cookie3 format text file.

        :param cookie_storage: file location string or CookieJar instance.
        """
        def toPyCookieJar(QtCookieJar, PyCookieJar):
            for c in QtCookieJar.allCookies():
                PyCookieJar.set_cookie(toPyCookie(c))

        def toPyCookie(QtCookie):
            port = None
            port_specified = False
            secure = QtCookie.isSecure()
            name = str(QtCookie.name())
            value = str(QtCookie.value())
            v = str(QtCookie.path())
            path_specified = bool(v != "")
            path = v if path_specified else None
            v = str(QtCookie.domain())
            domain_specified = bool(v != "")
            domain = v
            if domain_specified:
                domain_initial_dot = v.startswith('.')
            else:
                domain_initial_dot = None
            v = long(QtCookie.expirationDate().toTime_t())
            # Long type boundary on 32bit platfroms; avoid ValueError
            expires = 2147483647 if v > 2147483647 else v
            rest = {}
            discard = False
            return Cookie(0, name, value, port, port_specified, domain,
                    domain_specified, domain_initial_dot, path, path_specified,
                    secure, expires, discard, None, None, rest)

        if cookie_storage.__class__.__name__ == 'str':
            cj = LWPCookieJar(cookie_storage)
            toPyCookieJar(self.cookie_jar, cj)
            cj.save()
        elif cookie_storage.__class__.__name__.endswith('CookieJar'):
            toPyCookieJar(self.cookie_jar, cookie_storage)
        else:
            raise ValueError('unsupported cookie_storage type.')

    @can_load_page
    def set_field_value(self, selector, value, blur=True):
        """Sets the value of the field matched by given selector.

        :param selector: A CSS selector that target the field.
        :param value: The value to fill in.
        :param blur: An optional boolean that force blur when filled in.
        """
        def _set_checkbox_value(el, value):
            el.setFocus()
            if value is True:
                el.setAttribute('checked', 'checked')
            else:
                el.removeAttribute('checked')

        def _set_checkboxes_value(els, value):
            for el in els:
                if el.attribute('value') == value:
                    _set_checkbox_value(el, True)
                else:
                    _set_checkbox_value(el, False)

        def _set_radio_value(els, value):
            for el in els:
                if el.attribute('value') == value:
                    el.setFocus()
                    el.setAttribute('checked', 'checked')

        def _set_text_value(el, value):
            el.setFocus()
            el.setAttribute('value', value)

        def _set_select_value(el, value):
            el.setFocus()
            self.evaluate('document.querySelector(%s).value = %s;' %
                (repr(selector), repr(value)))

        def _set_textarea_value(el, value):
            el.setFocus()
            el.setPlainText(value)

        res, ressources = None, []
        element = self.main_frame.findFirstElement(selector)
        if element.isNull():
            raise Error('can\'t find element for %s"' % selector)

        tag_name = str(element.tagName()).lower()

        if tag_name == "select":
            _set_select_value(element, value)
        elif tag_name == "textarea":
            _set_textarea_value(element, value)
        elif tag_name == "input":
            type_ = str(element.attribute('type')).lower()
            if type_ in [
                "color", "date", "datetime",
                "datetime-local", "email", "hidden", "month", "number",
                "password", "range", "search", "tel", "text", "time",
                "url", "week", ""]:
                _set_text_value(element, value)
            elif type_ == "checkbox":
                els = self.main_frame.findAllElements(selector)
                if els.count() > 1:
                    _set_checkboxes_value(els, value)
                else:
                    _set_checkbox_value(element, value)
            elif type_ == "radio":
                _set_radio_value(self.main_frame.findAllElements(selector),
                    value)
            elif type_ == "file":
                Ghost._upload_file = value
                res, resources = self.click(selector)
                Ghost._upload_file = None
        else:
            raise Error('unsuported field tag')
        if blur:
            self.fire_on(selector, 'blur')
        return res, ressources

    def set_proxy(self, type_, host='localhost', port=8888, user='',
            password=''):
        """Set up proxy for FURTHER connections.

        :param type_: proxy type to use: \
            none/default/socks5/https/http.
        :param host: proxy server ip or host name.
        :param port: proxy port.
        """
        _types = {
            'default': QNetworkProxy.DefaultProxy,
            'none': QNetworkProxy.NoProxy,
            'socks5': QNetworkProxy.Socks5Proxy,
            'https': QNetworkProxy.HttpProxy,
            'http': QNetworkProxy.HttpCachingProxy
        }

        if type_ is None:
            type_ = 'none'
        type_ = type_.lower()
        if type_ in ['none', 'default']:
            self.manager.setProxy(QNetworkProxy(_types[type_]))
            return
        elif type_ in _types:
            proxy = QNetworkProxy(_types[type_], hostName=host, port=port,
                user=user, password=password)
            self.manager.setProxy(proxy)
        else:
            raise ValueError('Unsupported proxy type:' + type_ \
            + '\nsupported types are: none/socks5/http/https/default')

    def set_viewport_size(self, width, height):
        """Sets the page viewport size.

        :param width: An integer that sets width pixel count.
        :param height: An integer that sets height pixel count.
        """
        self.page.setViewportSize(QSize(width, height))

    def append_popup_message(self, message):
        self.popup_messages.append(unicode(message))

    def show(self):
        """Show current page inside a QWebView.
        """
        self.webview.show()

    def sleep(self, value):
        started_at = time.time()

        time.sleep(0)
        Ghost._app.processEvents()
        while time.time() <= (started_at + value):
            time.sleep(0.01)
            Ghost._app.processEvents()

    def wait_for(self, condition, timeout_message):
        """Waits until condition is True.

        :param condition: A callable that returns the condition.
        :param timeout_message: The exception message on timeout.
        """
        started_at = time.time()
        while not condition():
            if time.time() > (started_at + self.wait_timeout):
                raise TimeoutError(timeout_message)
            time.sleep(0.01)
            Ghost._app.processEvents()
            if self.wait_callback is not None:
                self.wait_callback()

    def wait_for_alert(self):
        """Waits for main frame alert().
        """
        self.wait_for(lambda: Ghost._alert is not None,
                      'User has not been alerted.')
        msg = Ghost._alert
        Ghost._alert = None
        return msg, self._release_last_resources()

    def wait_for_page_loaded(self):
        """Waits until page is loaded, assumed that a page as been requested.
        """
        self.wait_for(lambda: self.loaded,
                      'Unable to load requested page')
        resources = self._release_last_resources()
        page = None

        url = self.main_frame.url().toString()
        url_without_hash = url.split("#")[0]

        for resource in resources:
            if url == resource.url or url_without_hash == resource.url:
                page = resource
        return page, resources

    def wait_for_selector(self, selector):
        """Waits until selector match an element on the frame.

        :param selector: The selector to wait for.
        """
        self.wait_for(lambda: self.exists(selector),
            'Can\'t find element matching "%s"' % selector)
        return True, self._release_last_resources()

    def wait_while_selector(self, selector):
        """Waits until the selector no longer matches an element on the frame.

        :param selector: The selector to wait for.
        """
        self.wait_for(lambda: not self.exists(selector),
            'Element matching "%s" is still available' % selector)
        return True, self._release_last_resources()

    def wait_for_text(self, text):
        """Waits until given text appear on main frame.

        :param text: The text to wait for.
        """
        self.wait_for(lambda: text in self.content,
            'Can\'t find "%s" in current frame' % text)
        return True, self._release_last_resources()

    def _authenticate(self, mix, authenticator):
        """Called back on basic / proxy http auth.

        :param mix: The QNetworkReply or QNetworkProxy object.
        :param authenticator: The QAuthenticator object.
        """
        if self._auth is not None and self._auth_attempt == 0:
            username, password = self._auth
            authenticator.setUser(username)
            authenticator.setPassword(password)
            self._auth_attempt += 1

    def _page_loaded(self):
        """Called back when page is loaded.
        """
        self.loaded = True
        if self.cache:
            self.cache.clear()

    def _page_load_started(self):
        """Called back when page load started.
        """
        self.loaded = False

    def _release_last_resources(self):
        """Releases last loaded resources.

        :return: The released resources.
        """
        last_resources = self.http_resources
        self.http_resources = []
        return last_resources

    def _request_ended(self, reply):
        """Adds an HttpResource object to http_resources.

        :param reply: The QNetworkReply object.
        """

        if reply.attribute(QNetworkRequest.HttpStatusCodeAttribute):
            Logger.log("[%s] bytesAvailable()= %s" % (str(reply.url()),
                reply.bytesAvailable()), level="debug")

            # Some web pages return cache headers that mandates not to cache
            # the reply, which means we won't find this QNetworkReply in
            # the cache object. In this case bytesAvailable will return > 0.
            # Such pages are www.etsy.com
            # This is a bit of a hack and due to the async nature of QT, might
            # not work at times. We should move to using some proxied
            # implementation of QNetworkManager and QNetworkReply in order to
            # get the contents of the requests properly rather than relying
            # on the cache.
            if reply.bytesAvailable() > 0:
                content = reply.peek(reply.bytesAvailable())
            else:
                content = None
            self.http_resources.append(HttpResource(reply, self.cache,
                                                    content=content))

    def _unsupported_content(self, reply):
        reply.readyRead.connect(
            lambda reply=reply: self._reply_download_content(reply))

    def _reply_download_content(self, reply):
        """Adds an HttpResource object to http_resources with unsupported
        content.

        :param reply: The QNetworkReply object.
        """
        if reply.attribute(QNetworkRequest.HttpStatusCodeAttribute):
            self.http_resources.append(HttpResource(reply, self.cache,
                                                    reply.readAll()))

    def _on_manager_ssl_errors(self, reply, errors):
        url = unicode(reply.url().toString())
        if self.ignore_ssl_errors:
            reply.ignoreSslErrors()
        else:
            Logger.log('SSL certificate error: %s' % url, level='warning')
