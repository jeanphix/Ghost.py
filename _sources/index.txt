.. Ghost.py documentation master file, created by
   sphinx-quickstart on Sun Nov 27 11:08:59 2011.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

========
ghost.py
========

.. include:: ../README.rst

-------------
Documentation
-------------

Installation
============

First you need to install PyQt_ that is available for many plateforms.

.. _PyQt: http://www.riverbankcomputing.co.uk/software/pyqt/intro

Then you may install ghost.py using pip::

    pip install git+git://github.com/jean-philippe/Ghost.py.git#egg=ghost


Quick start
============

ghost.py provides a simple webkit based web client named Ghost::

    from ghost import Ghost
    ghost = Ghost()


Sample use case
---------------

The following test tries to center http://www.openstreetmap.org/ map to France::

    # Opens the web page
    ghost.open('http://www.openstreetmap.org/')
    # Waits for form search field
    ghost.wait_for_selector('input[name=query]')
    # Fills the form
    ghost.fill("#search_form", {'query': 'France'})
    # Submits the form
    ghost.fire_on("#search_form", "submit")
    # Waits for results (an XHR has been called here)
    ghost.wait_for_selector(
        '#search_osm_nominatim .search_results_entry a')
    # Clicks first result link
    ghost.click(
        '#search_osm_nominatim .search_results_entry:first-child a')
    # Checks if map has moved to expected latitude
    lat, ressources = ghost.evaluate("map.center.lat")
    assert float(lat.toString()) == 5860090.806537


Testing your WSGI apps
======================

Requirements::

    pip install tornado

ghost.py provides a simple GhostTestCase that deals with WSGI applications::

    from flask import Flask
    from ghost import GhostTestCase


    app = Flask(__name__)

    @app.route('/')
    def home():
        return 'hello world'


    class MyTest(GhostTestCase):
        port = 5000

        def create_app(self):
            return app

        def test_open_home(self):
            self.ghost.open("http://localhost:%s/" % self.port)
            self.assertEqual(self.ghost.content, 'hello world')


    if __name__ == '__main__':
        unittest.main()


Api
===

.. autoclass:: ghost.ghost.Ghost
   :members:


.. autoclass:: ghost.test.GhostTestCase
   :members:


Running API test suite
----------------------

Package tests require Flask an tornado available via::

    pip install Flask tornado

Then::

    cd tests
    python run.py