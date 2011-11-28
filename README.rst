ghost.py is a python web client inspired by Casper.js::

    from ghost import Ghost
    ghost = Ghost()
    page, ressources = ghost.open("http://jeanphi.fr")
    assert page.http_status==200 and 'jeanphix' in ghost.content