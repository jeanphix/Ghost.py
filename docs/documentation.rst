=============
Documentation
=============

------------
Installation
------------

First you need to install PyQt_ that is available for many plateforms.

.. _PyQt: http://www.riverbankcomputing.co.uk/software/pyqt/intro

Then you may install ghost.by using pip::

    pip install ghost.py


-----------
Quick start
-----------

ghost.py provides a simple webkit based web client named Ghost::

    from ghost import Ghost
    ghost = Ghost()


Sample use case
===============

In the following, we'll query http://www.openstreetmap.org/ for center map to France::

    # Opens the web page
    ghost.open('http://www.openstreetmap.org/')
    # Waits form serach field
    ghost.wait_for_selector('input[name=query]')
    # Fills the form
    ghost.fill("#search_form", {'query': 'France'})
    # Submits the form
    ghost.fire_on("#search_form", "submit")
    # Waits for results (an XHR has been called here)
    r, ressources = self.ghost.wait_for_selector(
        '#search_osm_nominatim .search_results_entry a')
    # Clicks first result link
    self.ghost.click(
        '#search_osm_nominatim .search_results_entry:first-child a')
    # Checks if map has moved to right latitude
    lat, ressources = self.ghost.evaluate("map.center.lat")
    assert float(lat.toString()) == 5860090.806537

Api
---

.. autoclass:: ghost.Ghost
   :members:
