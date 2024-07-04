from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)

bp = Blueprint("welcome", __name__, url_prefix="/")

'''
Welcome page, redirect to login.
'''
@bp.route('/welcome')
def index():
    # TODO: this first line should be included in the html somehow, but that also has to be 
    # up and running, if that makes any sense at all. 
    # return "Welcome to RecordRecs <a href='/login'>Login with Spotify</a>" 
    return render_template('welcome/welcome.html')

'''
yes, this makes sense. 
At the very beginning, I just want to return the home page, that will include a link
that will lead the user to the login with spotify, then, the recommendations will
be returned but in a fancy way on the web page
other features could include search capability, 
and then also the ability to refresh and get another round of recs. 
so yes, i def have my work cut out for me here. 
'''

'''
so maybe the first "goal" could be to just get the whole structure and flow set up
and then after that i can work more on the look of the whole website and all of that jazz
'''