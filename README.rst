ghost.py
========

ghost.py is a webkit web client written in python::

    from ghost import Ghost
    ghost = Ghost()
    page, extra_resources = ghost.open("http://jeanphix.me")
    assert page.http_status==200 and 'jeanphix' in ghost.content

.. image:: https://drone.io/github.com/jeanphix/Ghost.py/status.png
   :target: https://drone.io/github.com/jeanphix/Ghost.py/latest


Installation
------------

ghost.py requires either PySide_ (prefered) or PyQt_ Qt_ bindings::

    pip install pyside ghost.py


.. _PySide: https://pyside.github.io/
.. _PyQt: http://www.riverbankcomputing.co.uk/software/pyqt/intro
.. _Qt: http://qt-project.org/
