ghost.py is a webkit python web client::

    from ghost import Ghost
    ghost = Ghost()
    page, ressources = ghost.open("http://jeanphi.fr")
    assert page.http_status==200 and 'jeanphix' in ghost.content

As ghost.py as been designed to be a python test client, please consider using another library like Casper.js_ for any other stuff (sniffing...).

.. _Casper.js: http://n1k0.github.com/casperjs/