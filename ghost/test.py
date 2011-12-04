# -*- coding: utf-8 -*-
import thread
from unittest import TestCase
from tornado.wsgi import WSGIContainer
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from ghost import Ghost


class GhostTestCase(TestCase):
    """TestCase that provides a ghost instance and manage
    an HTTPServer running a WSGI application.
    """
    port = 5000
    display = False

    def __call__(self, result=None):
        """Does the required setup, doing it here
        means you don't have to call super.setUp
        in subclasses.
        """
        try:
            self._pre_setup()
            super(GhostTestCase, self).__call__(result)
        finally:
            self._post_teardown()

    def create_app(self):
        """Returns your WSGI application for testing.
        """
        raise NotImplementedError

    def _post_teardown(self):
        """Stops HTTPServer instance."""
        self.http_server.stop()
        if self.display:
            self.ghost.close_webview()

    def _pre_setup(self):
        """Starts HTTPServer instance from WSGI application.
        """
        self.ghost = Ghost(display=self.display)
        self.app = self.create_app()
        self.http_server = HTTPServer(WSGIContainer(self.app))
        self.http_server.listen(self.port)
        self.io = IOLoop.instance()
        thread.start_new_thread(lambda io: io.start(), (self.io,))
