# -*- coding: utf-8 -*-
from flask import Flask, render_template, url_for, redirect


app = Flask(__name__)


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/redirect-me')
def redirect_me():
    return redirect(url_for('home'))


if __name__ == '__main__':
    app.run()
