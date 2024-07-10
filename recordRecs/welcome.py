from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)

bp = Blueprint("welcome", __name__, url_prefix="/")

'''
Welcome page, redirect to login.
'''
@bp.route('/welcome')
def index():
    return render_template('welcome/welcome.html')