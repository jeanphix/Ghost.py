# -*- coding: utf-8 -*-
import sys
import os

from flask import (
    abort,
    flash,
    Flask,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    Response,
    url_for,
)

from werkzeug.datastructures import Headers


PY3 = sys.version > '3'


app = Flask(__name__)
app.config['CSRF_ENABLED'] = False
app.config['SECRET_KEY'] = 'asecret'


@app.route('/', methods=['get', 'post'])
def home():
    if request.method == 'POST':
        flash('Form successfully sent.')
        file = request.files.get('simple-file')
        if file is not None:
            file.save(os.path.join(
                os.path.dirname(__file__),
                "uploaded_%s" % file.filename
            ))
        return redirect(url_for('home'))
    return render_template('home.html')


@app.route('/echo/<arg>')
def echo(arg):
    return render_template('echo.html', arg=arg)


@app.route('/no-cache')
def no_cache():
    response = make_response("No cache for me.", 200)
    response.headers['Cache-Control'] = (
        'no-store, no-cache, must-revalidate, post-check=0, pre-check=0'
    )
    return response


@app.route('/cookie')
def cookie():
    resp = make_response('Response text')
    resp.set_cookie('mycookies', 'mycookie value')
    return resp


@app.route('/set/cookie')
def set_cookie():
    resp = make_response('Response text')
    resp.set_cookie('_path', value='/get/', path='/get/')
    resp.set_cookie('_path_fail', value='/set/', path='/set/')
    resp.set_cookie('_domain', value='127.0.0.1')
    resp.set_cookie('_secure_fail', value='sslonly', secure=True)
    resp.set_cookie('_expires', value='2147483647', expires=2147483647)
    return resp


@app.route('/get/cookie')
def get_cookie():
    cookies = {
        '_expires': '2147483647',
        '_domain': '127.0.0.1',
        '_path': '/get/',
    }
    # make sure only what we expect is received.
    if cookies != request.cookies:
        return make_response('FAIL')
        # print request.cookies
    else:
        return make_response('OK')


@app.route('/protected')
def protected():
    return abort(403)


@app.route('/settimeout')
def settimeout():
    return render_template('settimeout.html')


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
    file_path = os.path.join(os.path.dirname(__file__), 'static', 'foo.tar.gz')
    f = open(file_path, 'rb')
    return Response(f, headers=h)


@app.route('/url-hash')
def url_hash():
    return render_template('url_hash.html')


@app.route('/url-hash-header')
def url_hash_header():
    response = make_response("Redirecting.", 302)
    response.headers['Location'] = url_for('echo', arg='Welcome') + "#/"
    return response


@app.route('/many-assets')
def many_assets():
    return render_template(
        'many_assets.html',
        css=['css%s' % i for i in range(0, 5)],
        js=['js%s' % i for i in range(0, 5)]
    )


@app.route('/js/<name>.js')
def js_assets(name=None):
    return 'var foo = "%s";' % name


@app.route('/css/<name>.css')
def css_assets(name=None):
    return 'P.%s { color: red; };' % name


@app.route('/dump')
def dump():
    return jsonify(dict(headers=dict(request.headers)))


if __name__ == '__main__':
    app.run()
