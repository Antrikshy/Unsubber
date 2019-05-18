import os

from flask import Flask, request, render_template, make_response, redirect
import requests


app = Flask(__name__)

_REDDIT_AUTH_URL_TEMPLATE = 'https://www.reddit.com/api/v1/authorize?client_id={}&response_type={}&state={}&redirect_uri={}&duration={}&scope={}'
_APP_CLIENT_ID = os.environ['UNSUBBER_CLIENT_ID']
# TODO: Remove this from app ^^^
_APP_CLIENT_SECRET = os.environ['UNSUBBER_CLIENT_SECRET']
# TODO: Remove this from app ^^^
_APP_REDIRECT_URL = 'http://127.0.0.1:5000/oauth-redirect'
# TODO: Remove this from app ^^^

def _generate_reddit_oauth_url():
    return _REDDIT_AUTH_URL_TEMPLATE.format(
        _APP_CLIENT_ID,
        'code',
        'login',
        _APP_REDIRECT_URL,
        'temporary',
        'mysubreddits,subscribe'
    )

def _generate_reddit_auth_code_payload(code):
    return {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': _APP_REDIRECT_URL
    }


# ------------------------------------------
# -------- PAGE RENDERING AND LOGIN --------
# ------------------------------------------

@app.route('/')
def render_login():
    return render_template('login.html')

@app.route('/login')
def redirect_to_login():
    return redirect(_generate_reddit_oauth_url())

@app.route('/unsub')
def render_main_app():
    token = request.cookies.get('access_token')
    if token is None:
        return redirect('/')
    return render_template('main.html')

@app.route('/oauth-redirect')
def handle_redirect():
    code = request.args.get('code')
    state = request.args.get('state')
    auth_res = requests.post('https://www.reddit.com/api/v1/access_token',
        auth=requests.auth.HTTPBasicAuth(_APP_CLIENT_ID, _APP_CLIENT_SECRET),
        data=_generate_reddit_auth_code_payload(code),
        headers={'User-Agent': 'Unsubber by u/Antrikshy'}
    )
    token = auth_res.json()['access_token']
    res = make_response(redirect('/unsub'))
    res.set_cookie('access_token', token)
    return res


# ------------------------------------------
# ------------- MAIN ENDPOINTS -------------
# ------------------------------------------

@app.route('/my-subreddits')
def get_subreddits():
    pass

@app.route('/get-subreddit-state')
def get_subreddit_state():
    pass

@app.route('/unsubscribe')
def unsubscribe_from_subreddit():
    pass
