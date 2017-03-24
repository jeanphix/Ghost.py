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

ghost.py requires either PySide (preferred, but only supported on python 2.6, 2.7, 3.2, 3.3, and 3.4) or PyQt4_ (NOT PyQt 5) Qt_ bindings:

.. code:: bash

    pip install pyside
    pip install ghost.py --pre

OSX:

.. code:: bash

    brew install qt
    mkvirtualenv foo
    pip install -U pip  # make sure pip is current
    pip install PySide
    pyside_postinstall.py -install
    pip install Ghost.py


.. _PySide: https://pyside.github.io/
.. _PyQt: http://www.riverbankcomputing.co.uk/software/pyqt/intro
.. _Qt: http://qt-project.org/
