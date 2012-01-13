# -*- coding: utf-8 -*-
try:
    from django.test import LiveServerTestCase
except ImportError:
    raise Exception("Ghost.py django extension requires django...")
from ghost.test import BaseGhostTestCase


class GhostTestCase(LiveServerTestCase, BaseGhostTestCase):
    pass
