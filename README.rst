ghost.py is a webkit web client written in python::

    from ghost import Ghost
    ghost = Ghost()
    page, extra_ressources = ghost.open("http://jeanphi.fr")
    assert page.http_status==200 and 'jeanphix' in ghost.content

As ghost.py has been designed to be a python web application test client, please consider using another library like Casper.js_ for any other stuff (sniffing...).

.. _Casper.js: http://n1k0.github.com/casperjs/