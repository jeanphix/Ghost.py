ghost.py is a webkit web client written in python::

    from ghost import Ghost
    ghost = Ghost()
    page, extra_resources = ghost.open("http://jeanphi.fr")
    assert page.http_status==200 and 'jeanphix' in ghost.content

.. image:: https://secure.travis-ci.org/jeanphix/Ghost.py.png
   :target: https://travis-ci.org/jeanphix/Ghost.py
