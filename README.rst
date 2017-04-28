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

The most convenient way to run ghost is to use the official docker image.

.. code:: bash

    docker run -i -t jeanphix/ghost.py:2.0.0-dev python3

    Python 3.5.2 (default, Nov 17 2016, 17:05:23)
    [GCC 5.4.0 20160609] on linux
    Type "help", "copyright", "credits" or "license" for more information.
    >>> from ghost import Ghost
    >>> g = Ghost()
    >>> with g.start() as session:
    ...     session.open('http://jeanphix.me')
    ...
    (<ghost.ghost.HttpResource object at 0x7f3a118fa128>, [<ghost.ghost.HttpResource object at 0x7f3a118fa128>, <ghost.ghost.HttpResource object at 0x7f3a118fa0f0>, <ghost.ghost.HttpResource object at 0x7f3a118fa160>, <ghost.ghost.HttpResource object at 0x7f3a118ec4e0>, <ghost.ghost.HttpResource object at 0x7f3a118ecfd0>])


.. _PySide2: https://wiki.qt.io/PySide2
.. _Qt5: https://www.qt.io/developers/
