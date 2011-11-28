# -*- coding: utf-8 -*-
import os
import thread
import time
import codecs
import json
from PyQt4 import QtWebKit
from PyQt4.QtNetwork import QNetworkRequest


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

    def javaScriptAlert(self, frame, msg):
        # super(GhostWebPage, self).javaScriptAlert(frame, msg)
        Logger.log("[Client page]: Javascript alert('%s')" % msg)

    def javaScriptConfirm(self, frame, msg):
        # super(GhostWebPage, self).javaScriptConfirm(frame, msg)
        Logger.log("[Client page]: Javascript confirm('%s')" % msg)
        Logger.log("[Client page]: You must specified a value for confirm"
            % msg, type="error")
        return True


def client_utils_required(func):
    """Decorator that checks avabality of Ghost client side utils,
    injects require javascript file instead.
    """
    def wrapper(self, *args, **kwargs):
        if not self.global_exists('GhostUtils'):
            self.evaluate(codecs.open('utils.js').read())
        return func(self, *args, **kwargs)
    return wrapper


class HttpRessource(object):
    """Represents an HTTP ressource.
    """
    def __init__(self, reply):
        self.url = unicode(reply.request().url().toString())
        self.http_status = reply.attribute(
            QNetworkRequest.HttpStatusCodeAttribute).toInt()[0]
        self._reply = reply


class Ghost(object):
    """Ghost manage a QtApplication executed on its own thread.

    :param wait_timeout: Maximum step duration in second.
    """
    lock = None
    command = None
    retval = None

    def __init__(self, wait_timeout=5):
        self.http_ressources = []

        self.wait_timeout = wait_timeout

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
    def click(self, selector):
        """Click the targeted element.

        :param selector: A CSS3 selector to targeted element.
        """
        return self.evaluate('GhostUtils.click("%s");' % selector)

    @property
    def content(self):
        """Gets current frame HTML as a string."""
        return unicode(self.main_frame.toHtml())

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
        :param submit: A boolean that force form submition.
        """
        return self.evaluate('GhostUtils.fill("%s", %s);' % (
            selector, unicode(json.dumps(values))))

    @client_utils_required
    def fire_on(self, selector, method, expect_page_loading=False):
        """Call method on element matching given selector.

        :param selector: A CSS selector to the target element.
        :param method: The name of the method to fire.
        :param expect_page_loading: Specifies if a page loading is expected.
        """
        if expect_page_loading:
            self.loaded = False
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
            self.main_frame.load(QNetworkRequest(QtCore.QUrl(address)),
                method, body)
            return self.page

        self.loaded = False
        self._run(open_page, True, *(self, address, method))
        return self.wait_for_page_loaded()

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
        from PyQt4 import QtWebKit

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

        self.main_frame = self.page.mainFrame()

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
