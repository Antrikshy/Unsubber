from flask import Flask, request, redirect
import requests

app = Flask(__name__)

_REDDIT_AUTH_URL_TEMPLATE = 'https://www.reddit.com/api/v1/authorize?client_id={}&response_type={}&state={}&redirect_uri={}&duration={}&scope={}'
_APP_CLIENT_ID = ''
# TODO: Remove this from app ^^^
_APP_CLIENT_SECRET = ''
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

@app.route('/login')
def hello_world():
    return redirect(_generate_reddit_oauth_url())

@app.route('/oauth-redirect')
def handle_redirect():
    code = request.args.get('code')
    state = request.args.get('state')
    auth_res = requests.post('https://www.reddit.com/api/v1/access_token',
        auth=requests.auth.HTTPBasicAuth(_APP_CLIENT_ID, _APP_CLIENT_SECRET),
        data=_generate_reddit_auth_code_payload(code),
        headers={'User-Agent': 'Unsubber (in-development) by u/Antrikshy'}
    )
    return auth_res.json()['access_token']
