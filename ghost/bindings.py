# -*- coding: utf-8 -*-

import os
import sys

PY3 = sys.version > '3'

if PY3:
    unicode = str
    long = int


binding = None

if 'GHOST_QT_PROVIDER' in os.environ:
    bindings = [os.environ['GHOST_QT_PROVIDER']]
else:
    bindings = ["PyQt5", "PySide", "PyQt4"]

for name in bindings:
    try:
        binding = __import__(name)
        if name.startswith('PyQt'):
            import sip
            sip.setapi('QVariant', 2)

    except ImportError:
        continue
    break


class LazyBinding(object):
    class __metaclass__(type):
        def __getattr__(self, name):
            return self.__class__

    def __getattr__(self, name):
        return self.__class__


def _import(name):
    if binding is None:
        return LazyBinding()

    name = "%s.%s" % (binding.__name__, name)
    module = __import__(name)
    for n in name.split(".")[1:]:
        module = getattr(module, n)
    return module


QtCore = _import("QtCore")
QSize = QtCore.QSize
QByteArray = QtCore.QByteArray
QUrl = QtCore.QUrl
QDateTime = QtCore.QDateTime
QtCriticalMsg = QtCore.QtCriticalMsg
QtDebugMsg = QtCore.QtDebugMsg
QtFatalMsg = QtCore.QtFatalMsg
QtWarningMsg = QtCore.QtWarningMsg
if name == "PyQt5":
    qInstallMsgHandler = QtCore.qInstallMessageHandler
else:
    qInstallMsgHandler = QtCore.qInstallMsgHandler

QtGui = _import("QtGui")
QImage = QtGui.QImage
QPainter = QtGui.QPainter
QRegion = QtGui.QRegion
if name == "PyQt5":
    QtWidgets = _import("QtWidgets")
    QtPrintSupport = _import("QtPrintSupport")
    QApplication = QtWidgets.QApplication
    QPrinter = QtPrintSupport.QPrinter
else:
    QApplication = QtGui.QApplication
    QPrinter = QtGui.QPrinter

QtNetwork = _import("QtNetwork")
QNetworkRequest = QtNetwork.QNetworkRequest
QNetworkAccessManager = QtNetwork.QNetworkAccessManager
QNetworkCookieJar = QtNetwork.QNetworkCookieJar
QNetworkProxy = QtNetwork.QNetworkProxy
QNetworkCookie = QtNetwork.QNetworkCookie
QSslConfiguration = QtNetwork.QSslConfiguration
QSsl = QtNetwork.QSsl

QtWebKit = _import('QtWebKit')
if name == "PyQt5":
    QtWebKitWidgets = _import("QtWebKitWidgets")
    QWebPage = QtWebKitWidgets.QWebPage
    QWebView = QtWebKitWidgets.QWebView
else:
    QWebPage = QtWebKit.QWebPage
    QWebView = QtWebKit.QWebView
