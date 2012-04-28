# -*- coding: utf-8 -*-
import os

from flask import Flask, render_template, url_for, redirect, jsonify
from flask import request, abort
from flask import make_response


app = Flask(__name__)
app.config['CSRF_ENABLED'] = False


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
        return redirect(url_for('form'))
    return render_template('form.html')


@app.route('/upload', methods=['get', 'post'])
def upload():
    if request.method == 'POST':
        file = request.files['simple-file']
        file.save(os.path.join(os.path.dirname(__file__),
            "uploaded_%s" % file.filename))
        return redirect(url_for('upload'))
    return render_template('upload.html')


@app.route('/redirect-me')
def redirect_me():
    return redirect(url_for('home'))


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
    if not _check_auth(auth.username, auth.password):
        abort(401)
    return '<p>successfully authenticated</p>'


if __name__ == '__main__':
    app.run()
