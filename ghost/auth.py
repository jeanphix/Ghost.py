# -*- coding: utf-8 -*-

"""HTTP auth utils.

Forked(/inspired) from kennethreitz/requests/auth.
"""

from base64 import b64encode


def _basic_auth_str(username, password):
    """Returns a Basic Auth string.
    """
    return 'Basic ' + b64encode(('%s:%s' % (username, password))\
        .encode('latin1')).strip().decode('latin1')


class BasicAuth(object):
    """Sets the HTTP basic auth header for given request."""
    def __init__(self, username, password):
        self.username = username
        self.password = password

    def __call__(self, request):
        request.setRawHeader('Authorization', _basic_auth_str(self.username,
            self.password))


class ProxyAuth(BasicAuth):
    """Sets the HTTP proxy auth header for given request."""
    def __call__(self, request):
        request.setRawHeader('Proxy-Authorization', _basic_auth_str(
            self.username, self.password))


def http_auth(request, auth_type, username, password):
    try:
        auth_class = globals()['%sAuth' % auth_type.capitalize()]
    except:
        raise Exception("Supported authentication are Basic, Proxy")
    return auth_class(username, password)(request)
