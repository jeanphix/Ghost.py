# -*- coding: utf-8 -*-
from flask import Flask, render_template, url_for, redirect, jsonify
from flask import request


app = Flask(__name__)
app.config['CSRF_ENABLED'] = False


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/form', methods=['get', 'post'])
def form():
    if request.method == 'POST':
        return redirect(url_for('form'))
    return render_template('form.html')


@app.route('/redirect-me')
def redirect_me():
    return redirect(url_for('home'))


@app.route('/mootools')
def mootools():
    return render_template('mootools.html')


@app.route('/items.json')
def items():
    return jsonify(items=['second item', 'third item'])


if __name__ == '__main__':
    app.run()
