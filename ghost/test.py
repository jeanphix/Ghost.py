# -*- coding: utf-8 -*-
import logging
import select
import threading
import time
from unittest import TestCase
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server

from ghost import Ghost


class GhostWSGIServer(WSGIServer):
    """Server class that integrates error handling with logging."""

    logger = logging.getLogger('ghost.test.wsgi.server')

    def handle_error(self, request, client_address):
        # Interpose base class method so that the exception gets printed to
        # our log file rather than stderr.
        self.logger.exception('REST server exception during request from %s',
                              client_address)


class StderrLogger(object):
    """File-like redirecting data written to it to logging."""

    logger = logging.getLogger('ghost.test.wsgi.request')

    def __init__(self):
        self._buffer = []

    def write(self, message):
        self._buffer.append(message)

    def flush(self):
        self._buffer.insert(0, 'REST request handler error:\n')
        self.logger.error(''.join(self._buffer))
        self._buffer = []


class GhostWSGIRequestHandler(WSGIRequestHandler):
    """Handle logs and timeout errors gracefully."""

    logger = logging.getLogger('ghost.test.wsgi.request')

    def handle(self):
        fd_sets = select.select([self.rfile], [], [], 1.0)
        if not fd_sets[0]:
            # Sometimes WebKit times out waiting for us.
            return

        super().handle()

    def log_request(self, code='-', size='-'):
        self.log_message(logging.DEBUG, '"%s" %s %s',
                         self.requestline, str(code), str(size))

    def log_error(self, format_, *args):
        self.log_message(logging.ERROR, format_, *args)

    def log_message(self, log_level, format_, *args):
        self.logger.log(log_level, format_, *args)

    def get_stderr(self):
        # Return a fake stderr object that will actually write its output to
        # the log file.
        return StderrLogger()


class ServerThread(threading.Thread):
    """Starts given WSGI application.

    :param app: The WSGI application to run.
    :param port: The port to run on.
    """
    def __init__(self, app, port=5000):
        self.app = app
        self.port = port
        super(ServerThread, self).__init__()

    def run(self):
        self.http_server = make_server(
            'localhost',
            self.port,
            self.app,
            server_class=GhostWSGIServer,
            handler_class=GhostWSGIRequestHandler,
        )
        self.http_server.serve_forever()

    def join(self, timeout=None):
        if hasattr(self, 'http_server'):
            self.http_server.shutdown()
            del self.http_server


class BaseGhostTestCase(TestCase):
    display = False
    wait_timeout = 5

    def __new__(cls, *args, **kwargs):
        """Creates Ghost instance."""
        if not hasattr(cls, 'ghost'):
            cls.ghost = Ghost(
                defaults=dict(
                    display=cls.display,
                    wait_timeout=cls.wait_timeout,
                )
            )

        return super(BaseGhostTestCase, cls).__new__(cls)

    def __call__(self, result=None):
        """Does the required setup, doing it here
        means you don't have to call super.setUp
        in subclasses.
        """
        self._pre_setup()
        try:
            super(BaseGhostTestCase, self).__call__(result)
        finally:
            self._post_teardown()

    def _post_teardown(self):
        """Deletes ghost cookies and hide UI if needed."""
        self.session.exit()

    def _pre_setup(self):
        """Shows UI if needed.
        """
        self.session = self.ghost.start()
        if self.display:
            self.session.show()


class GhostTestCase(BaseGhostTestCase):
    """TestCase that provides a ghost instance and manage
    an HTTPServer running a WSGI application.
    """
    server_class = ServerThread
    port = 5000

    def create_app(self):
        """Returns your WSGI application for testing.
        """
        raise NotImplementedError

    @classmethod
    def tearDownClass(cls):
        """Stops HTTPServer instance."""
        cls.server_thread.join()
        super(GhostTestCase, cls).tearDownClass()

    @classmethod
    def setUpClass(cls):
        """Starts HTTPServer instance from WSGI application.
        """
        cls.server_thread = cls.server_class(cls.create_app(), cls.port)
        cls.server_thread.daemon = True
        cls.server_thread.start()
        while not hasattr(cls.server_thread, 'http_server'):
            time.sleep(0.01)
        super(GhostTestCase, cls).setUpClass()
