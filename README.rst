ghost.py
========

.. image:: https://travis-ci.org/jeanphix/Ghost.py.svg?branch=master
   :target: https://travis-ci.org/jeanphix/Ghost.py
   :alt: Build Status


ghost.py is a webkit web client written in python:

.. code:: python

    from ghost import Ghost
    ghost = Ghost()

    with ghost.start() as session:
        page, extra_resources = session.open("http://jeanphix.me")
        assert page.http_status == 200 and 'jeanphix' in page.content


Installation
------------

ghost.py requires PySide2_ Qt5_ bindings.

.. _PySide2: https://wiki.qt.io/PySide2
.. _Qt5: https://www.qt.io/developers/
