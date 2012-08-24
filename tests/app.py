# -*- coding: utf-8 -*-
import os

from flask import Flask, render_template, url_for, redirect, jsonify
from flask import request, abort, Response, flash
from flask import make_response

from werkzeug import Headers


app = Flask(__name__)
app.config['CSRF_ENABLED'] = False
app.config['SECRET_KEY'] = 'asecret'


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/alert')
def alert():
    return render_template('alert.html')


@app.route('/cookie')
def cookie():
    resp = make_response('Response text')
    resp.set_cookie('mycookies', 'mycookie value')
    return resp


@app.route('/form', methods=['get', 'post'])
def form():
    if request.method == 'POST':
        flash('form successfully posted')
        return redirect(url_for('form'))
    return render_template('form.html')


@app.route('/image')
def image():
    return render_template('image.html')


@app.route('/upload', methods=['get', 'post'])
def upload():
    if request.method == 'POST':
        file = request.files['simple-file']
        file.save(os.path.join(os.path.dirname(__file__),
            "uploaded_%s" % file.filename))
        return redirect(url_for('upload'))
    return render_template('upload.html')


@app.route('/protected')
def protected():
    return abort(403)


@app.route('/mootools')
def mootools():
    return render_template('mootools.html')


@app.route('/items.json')
def items():
    return jsonify(items=['second item', 'third item'])


def _check_auth(username, password):
    return username == 'admin' and password == 'secret'


@app.route('/basic-auth')
def basic_auth():
    auth = request.authorization
    if auth is None or not _check_auth(auth.username, auth.password):
        return Response(
            'Could not verify your access level for that URL.\n'
            'You have to login with proper credentials', 401,
            {'WWW-Authenticate': 'Basic realm="Login Required"'})
    return '<p>successfully authenticated</p>'


@app.route('/send-file')
def send_file():
    h = Headers()
    h.add('Content-type', 'application/octet-stream', charset='utf8')
    h.add('Content-disposition', 'attachment', filename='name.tar.gz')
    return Response(open(os.path.join(os.path.dirname(__file__), 'static',
        'foo.tar.gz'), 'r'), headers=h)


if __name__ == '__main__':
    app.run()
