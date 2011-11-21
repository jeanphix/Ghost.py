import os
import thread
import time
from PyQt4 import QtCore
from PyQt4.QtNetwork import QNetworkRequest

class HttpRessource(object):
    """Represents an HTTP response.
    """
    def __init__(self, reply):
        self.url = unicode(reply.request().url().toString())
        self.http_status = reply.attribute(
            QNetworkRequest.HttpStatusCodeAttribute).toInt()[0]
        self._reply = reply


class Casper(object):
    """Casper manage a QtApplication executed on its own thread.
    """
    lock = None
    command = None
    retval = None

    def __init__(self):
        self.http_responses = []

        if not Casper.lock:
            Casper.lock = thread.allocate_lock()

            # To Qt thread pipe
            Casper.pipetoveusz_r, w = os.pipe()
            Casper.pipetoveusz_w = os.fdopen(w, 'w', 0)

            # Return pipe
            r, w = os.pipe()
            Casper.pipefromveusz_r = os.fdopen(r, 'r', 0)
            Casper.pipefromveusz_w = os.fdopen(w, 'w', 0)

            thread.start_new_thread(Casper._start, (self,))
            # As there's no callback on application started,
            # lets leep for a while...
            # TODO: fix this
            time.sleep(0.5)

    def open(self, address, callback=None, method='get'):
        def open_ressource(self, address, method):
            from PyQt4 import QtCore
            from PyQt4.QtNetwork import QNetworkAccessManager, QNetworkRequest
            body = QtCore.QByteArray()
            try:
                method = getattr(QNetworkAccessManager,
                    "%sOperation" % method.capitalize())
            except AttributeError:
                raise Exception("Invalid http method %s" % method)
            self.page.mainFrame().load(QNetworkRequest(QtCore.QUrl(address)),
                method, body)
            return self.page

        return self._run(open_ressource, False, *(self, address, method))

    @property
    def content(self):
        return unicode(self.page.mainFrame().toHtml())

    def _run(self, cmd, releasable, *args, **kwargs):
        """Execute the given command in the Qt thread."""
        assert Casper.command == None and Casper.retval == None
        # Sends the command to Qt thread
        Casper.lock.acquire()
        Casper.command = (cmd, releasable, args, kwargs)
        Casper.lock.release()
        Casper.pipetoveusz_w.write('N')
        # Waits for command to be executed
        Casper.pipefromveusz_r.read(1)
        Casper.lock.acquire()
        retval = Casper.retval
        Casper.command = None
        Casper.retval = None
        Casper.lock.release()
        if isinstance(retval, Exception):
            raise retval
        else:
            return retval

    def _start(self):
        """Starts a QtApplication on the dedicated thread.

        Imports have to be done inside thread.
        """
        from PyQt4 import QtCore
        from PyQt4 import QtGui
        from PyQt4 import QtWebKit

        class CasperApp(QtGui.QApplication):
            def notification(self, i):
                """Notifies application from main thread calls.
                """
                Casper.lock.acquire()
                os.read(Casper.pipetoveusz_r, 1)

                assert Casper.command is not None
                cmd, releasable, args, kwargs = Casper.command
                try:
                    Casper.retval = cmd(*args, **kwargs)
                except Exception, e:
                    Casper.retval = e

                if releasable:
                    Casper._release()

        app = CasperApp(['casper'])
        notifier = QtCore.QSocketNotifier(Casper.pipetoveusz_r,
                                       QtCore.QSocketNotifier.Read)
        app.connect(notifier, QtCore.SIGNAL('activated(int)'),
            app.notification)
        notifier.setEnabled(True)

        self.page = QtWebKit.QWebPage(app)
        self.page.setViewportSize(QtCore.QSize(400, 300))

        self.page.loadFinished.connect(self._page_loaded)
        self.page.networkAccessManager().finished.connect(self._request_ended)

        app.exec_()

    def _page_loaded(self):
        """Call back main thread when page loaded.
        """
        Casper.retval = self.http_responses
        Casper._release()
        self.loaded_ressources = []

    @staticmethod
    def _release():
        Casper.lock.release()
        Casper.pipefromveusz_w.write('r')

    def _request_ended(self, res):
        """Adds an HttpResponse object to http_responses.
        """
        self.http_responses.append(HttpRessource(res))
