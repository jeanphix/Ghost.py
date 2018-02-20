# -*- coding: utf-8 -*-

import os


def _load_binding():
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
    else:
        name, binding = None, None

    return name, binding


BINDING_NAME, BINDING = _load_binding()


class LazyBinding(object):
    class __metaclass__(type):
        def __getattr__(self, name):
            return self.__class__

    def __getattr__(self, name):
        return self.__class__


def _import(name):
    if BINDING is None:
        return LazyBinding()

    name = "%s.%s" % (BINDING.__name__, name)
    module = __import__(name)
    for component in name.split(".")[1:]:
        module = getattr(module, component)
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
if BINDING_NAME == "PyQt5":
    qInstallMsgHandler = QtCore.qInstallMessageHandler
else:
    qInstallMsgHandler = QtCore.qInstallMsgHandler

QtGui = _import("QtGui")
QImage = QtGui.QImage
QPainter = QtGui.QPainter
QRegion = QtGui.QRegion
if BINDING_NAME == "PyQt5":
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
if BINDING_NAME == "PyQt5":
    QtWebKitWidgets = _import("QtWebKitWidgets")
    QWebPage = QtWebKitWidgets.QWebPage
    QWebView = QtWebKitWidgets.QWebView
else:
    QWebPage = QtWebKit.QWebPage
    QWebView = QtWebKit.QWebView
