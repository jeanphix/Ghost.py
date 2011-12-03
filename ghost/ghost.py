# -*- coding: utf-8 -*-
import os
import thread
import time
import codecs
import json
from functools import wraps
from PyQt4 import QtWebKit
from PyQt4.QtNetwork import QNetworkRequest


default_user_agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/535.2 " +\
    "(KHTML, like Gecko) Chrome/15.0.874.121 Safari/535.2"


class Logger(object):
    """Output colorized logs."""
    INFO = '\033[94m'  # Blue
    SUCCESS = '\033[92m'  # Green
    WARNING = '\033[93m'  # Yellow
    ERROR = '\033[91m'  # Red
    END = '\033[0m'

    @staticmethod
    def log(message, type="info"):
        """Sends given message to std ouput."""
        try:
            print "%s%s%s" % (getattr(Logger, type.upper()), message,
                Logger.END)
        except AttributeError:
            raise Exception("Invalid log type")


class GhostWebPage(QtWebKit.QWebPage):
    """Overrides QtWebKit.QWebPage in order to intercept some graphical
    behaviours like alert(), confirm().
    Also intercepts client side console.log().
    """
    def javaScriptConsoleMessage(self, message, *args, **kwargs):
        """Prints client console message in current output stream."""
        super(GhostWebPage, self).javaScriptConsoleMessage(message, *args,
        **kwargs)
        log_type = "error" if "Error" in message else "success"
        Logger.log("[Client javascript console]: %s" % message, type=log_type)

    def javaScriptAlert(self, frame, message):
        """Notifies ghost for alert, then pass."""
        Ghost.alert = message
        Logger.log("[Client page]: Javascript alert('%s')" % message)

    def javaScriptConfirm(self, frame, message):
        """Checks if ghost is waiting for confirm, then returns the right
        value.
        """
        if Ghost.confirm_expected is None:
            raise Exception('You must specified a value to confirm "%s"' %
                message)
        confirmation = Ghost.confirm_expected
        Ghost.confirm_expected = None
        return confirmation

    def javaScriptPrompt(self, frame, message, defaultValue, result):
        """Checks if ghost is waiting for prompt, then enters the right
        value.
        """
        if Ghost.prompt_expected is None:
            raise Exception('You must specified a value for prompt "%s"' %
                message)
        result.append(Ghost.prompt_expected)
        Ghost.prompt_expected = None
        return True


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
    """Ghost manage a QtApplication executed on its own thread.

    :param user_agent: The default User-Agent header.
    :param wait_timeout: Maximum step duration in second.
    :param display: A boolean that tells ghost to displays UI
    """
    lock = None
    command = None
    retval = None
    alert = None
    prompt = None
    confirm_expected = None
    prompt_expected = None

    def __init__(self, user_agent=default_user_agent, wait_timeout=5,
            display=True):
        self.http_ressources = []

        self.user_agent = user_agent
        self.wait_timeout = wait_timeout
        self.display = display

        self.loaded = False

        if not Ghost.lock:
            Ghost.lock = thread.allocate_lock()

            # To Qt thread pipe
            Ghost.pipetoveusz_r, w = os.pipe()
            Ghost.pipetoveusz_w = os.fdopen(w, 'w', 0)

            # Return pipe
            r, w = os.pipe()
            Ghost.pipefromveusz_r = os.fdopen(r, 'r', 0)
            Ghost.pipefromveusz_w = os.fdopen(w, 'w', 0)

            thread.start_new_thread(Ghost._start, (self,))
            # As there's no callback on application started,
            # lets sleep for a while...
            # TODO: fix this
            time.sleep(0.5)

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
        def __init__(self, confirm=True):
            self.confirm = confirm

        def __enter__(self):
            Ghost.confirm_expected = self.confirm

        def __exit__(self, type, value, traceback):
            Ghost.confirm_expected = None

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
    def evaluate(self, script, releasable=True):
        """Evaluates script in page frame.

        :param script: The script to evaluate.
        :param releasable: Specifies if callback waiting is needed.
        """
        return self._run(
                lambda self, script: self.main_frame\
                    .evaluateJavaScript("%s" % script),
                releasable, *(self, script)
            ), self._release_last_ressources()

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
        return not self._run(
                lambda self, selector: self.main_frame\
                    .findFirstElement(selector), True, *(self, selector)
            ).isNull()

    @client_utils_required
    def fill(self, selector, values):
        """Fills a form with provided values.

        :param selector: A CSS selector to the target form to fill.
        :param values: A dict containing the values.
        """
        if not self.exists(selector):
            raise Exception("Can't find form")
        return self.evaluate('GhostUtils.fill("%s", %s);' % (
            selector, unicode(json.dumps(values))))

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

    def open(self, address, method='get'):
        """Opens a web page.

        :param address: The ressource URL.
        :param method: The Http method.
        :return: Page ressource, All loaded ressources.
        """
        def open_page(self, address, method):
            from PyQt4 import QtCore
            from PyQt4.QtNetwork import QNetworkAccessManager, QNetworkRequest
            body = QtCore.QByteArray()
            try:
                method = getattr(QNetworkAccessManager,
                    "%sOperation" % method.capitalize())
            except AttributeError:
                raise Exception("Invalid http method %s" % method)
            request = QNetworkRequest(QtCore.QUrl(address))
            request.setRawHeader("User-Agent", self.user_agent)
            self.main_frame.load(request, method, body)
            return self.page

        self.loaded = False
        self._run(open_page, True, *(self, address, method))
        return self.wait_for_page_loaded()

    class prompt:
        def __init__(self, value):
            self.value = value

        def __enter__(self):
            Ghost.prompt_expected = self.value

        def __exit__(self, type, value, traceback):
            Ghost.prompt_expected = None

    def wait_for_alert(self):
        """Waits for main frame alert().
        """
        self._wait_for(lambda: Ghost.alert is not None,
            'User has not been alerted.')
        msg = Ghost.alert
        Ghost.alert = None
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

    def _run(self, cmd, releasable, *args, **kwargs):
        """Execute the given command in the Qt thread.

        :param cmd: The command to execute.
        :param releasable: Specifies if callback waiting is needed.
        """
        assert Ghost.command == None and Ghost.retval == None
        # Sends the command to Qt thread
        Ghost.lock.acquire()
        Ghost.command = (cmd, releasable, args, kwargs)
        Ghost.lock.release()
        Ghost.pipetoveusz_w.write('N')
        # Waits for command to be executed
        Ghost.pipefromveusz_r.read(1)
        Ghost.lock.acquire()
        retval = Ghost.retval
        Ghost.command = None
        Ghost.retval = None
        Ghost.lock.release()
        if isinstance(retval, Exception):
            raise retval
        else:
            return retval

    def _start(self):
        """Starts a QtApplication on the dedicated thread.

        :note: Imports have to be done inside thread.
        """
        from PyQt4 import QtCore
        from PyQt4 import QtGui
        from PyQt4 import QtNetwork

        class GhostApp(QtGui.QApplication):
            def notification(self, i):
                """Notifies application from main thread calls.
                """
                Ghost.lock.acquire()
                os.read(Ghost.pipetoveusz_r, 1)
                assert Ghost.command is not None
                cmd, releasable, args, kwargs = Ghost.command
                try:
                    Ghost.retval = cmd(*args, **kwargs)
                except Exception, e:
                    Ghost.retval = e

                if releasable:
                    Ghost._release()

        app = GhostApp(['ghost'])
        notifier = QtCore.QSocketNotifier(Ghost.pipetoveusz_r,
                                       QtCore.QSocketNotifier.Read)
        app.connect(notifier, QtCore.SIGNAL('activated(int)'),
            app.notification)
        notifier.setEnabled(True)

        self.page = GhostWebPage(app)
        self.page.setViewportSize(QtCore.QSize(400, 300))

        self.page.loadFinished.connect(self._page_loaded)
        self.page.loadStarted.connect(self._page_load_started)

        self.page.networkAccessManager().finished.connect(self._request_ended)

        self.cookie_jar = QtNetwork.QNetworkCookieJar()
        self.page.networkAccessManager().setCookieJar(self.cookie_jar)

        self.main_frame = self.page.mainFrame()

        if self.display:
            webview = QtWebKit.QWebView()
            webview.setPage(self.page)
            webview.show()
        app.exec_()

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

    @staticmethod
    def _release():
        """Releases the back pipe."""
        Ghost.lock.release()
        Ghost.pipefromveusz_w.write('r')

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
