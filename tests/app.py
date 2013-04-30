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

@app.route('/no-cache')
def no_cahce():
    response = make_response("No cache for me.", 200)
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0'
    return response

@app.route('/alert')
def alert():
    return render_template('alert.html')


@app.route('/cookie')
def cookie():
    resp = make_response('Response text')
    resp.set_cookie('mycookies', 'mycookie value')
    return resp

@app.route('/set/cookie')
def set_cookie():
    resp = make_response('Response text')
    resp.set_cookie('_path', value='/get/', path='/get/')
    resp.set_cookie('_path_fail', value='/set/', path='/set/' )
    resp.set_cookie('_domain', value='127.0.0.1' )
    resp.set_cookie('_secure_fail', value='sslonly', secure=True)
    resp.set_cookie('_expires', value='2147483647', expires=2147483647)
    return resp

@app.route('/get/cookie')
def get_cookie():
    cookies = { '_expires': '2147483647' \
    , '_domain': '127.0.0.1' \
    , '_path': '/get/'}
    # make sure only what we expect is received.
    if cookies != request.cookies:
        return make_response('FAIL')
        # print request.cookies
    else:
        return make_response('OK')

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

@app.route('/url-hash')
def url_hash():
    return render_template('url_hash.html')

@app.route('/url-hash-header')
def url_hash_header():
    response = make_response("Redirecting.", 302)
    response.headers['Location'] = url_for('url_hash_header_redirect') + "#/"
    return response

@app.route('/url-hash-header-redirect/')
def url_hash_header_redirect():
    return "Welcome."



if __name__ == '__main__':
    app.run()
