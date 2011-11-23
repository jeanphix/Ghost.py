# -*- coding: utf-8 -*-
from flask import Flask, render_template, url_for, redirect, jsonify


app = Flask(__name__)
app.debug = True


@app.route('/')
def home():
    return render_template('home.html')


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
