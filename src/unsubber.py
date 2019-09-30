import os
import itertools
import multiprocessing as mp

from flask import Flask, request, render_template, make_response, jsonify, redirect
import requests


app = Flask(__name__)

_REDDIT_ROOT_URL = 'https://www.reddit.com'
_REDDIT_OAUTH_ROOT_URL = 'https://oauth.reddit.com'
_REDDIT_AUTH_URL_TEMPLATE = _REDDIT_ROOT_URL + \
    '/api/v1/authorize?client_id={}&response_type={}&state={}&redirect_uri={}&duration={}&scope={}'
_APP_CLIENT_ID = os.environ['UNSUBBER_CLIENT_ID']
_APP_CLIENT_SECRET = os.environ['UNSUBBER_CLIENT_SECRET']
_APP_REDIRECT_URL = 'http://127.0.0.1:5000/oauth-redirect'
# TODO: Remove this from app ^^^
_APP_HTTP_REQUEST_HEADER = {'User-Agent': 'Unsubber (website; in-development) by u/Antrikshy'}


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


def _get_all_user_subreddits(access_token):
    headers = _APP_HTTP_REQUEST_HEADER.copy()
    headers['Authorization'] = 'Bearer ' + access_token
    after = ''
    subreddits = []
    while after is not None:
        url = _REDDIT_OAUTH_ROOT_URL + '/subreddits/mine/subscriber?raw_json=1&limit=100' + '&after=' + after
        res = requests.get(url, headers=headers)
        if res.status_code != 200:
            res.raise_for_status()
        j_res = res.json()
        after = j_res['data']['after']
        subreddits += [
            {
                'display_name': i['data']['display_name'],
                'subscribers': i['data']['subscribers']
            }
            for i in j_res['data']['children']
        ]
    return subreddits


def _is_subreddit_active(subreddit, access_token):
    # Reading response
    res = requests.get(f'{_REDDIT_ROOT_URL}/r/{subreddit}/new.json', headers=_APP_HTTP_REQUEST_HEADER)
    if res.status_code != 200:
        res.raise_for_status()
    j_res = res.json()
    # Reading subreddit and post metadata
    r_subreddit_data = j_res['data']['children']
    r_subreddit_subscribers = r_subreddit_data[0]['data']['subreddit_subscribers']
    r_post_created_collation = list(map(lambda post: post['data']['created'], r_subreddit_data))
    # Computing active state (aka #TheAlgorithm)
    subreddit_is_active = True
    if r_subreddit_subscribers < 200:
        subreddit_is_active = False
    return {'is_active': subreddit_is_active, 'subreddit': subreddit}


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
    auth_res = requests.post(_REDDIT_ROOT_URL + '/api/v1/access_token',
        auth=requests.auth.HTTPBasicAuth(_APP_CLIENT_ID, _APP_CLIENT_SECRET),
        data=_generate_reddit_auth_code_payload(code),
        headers=_APP_HTTP_REQUEST_HEADER
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
    token = request.cookies.get('access_token')
    try:
        subreddits = _get_all_user_subreddits(token)
        return jsonify(subreddits=subreddits)
    except requests.exceptions.HTTPError as e:
        res = make_response()
        res.status_code = e.status_code
        return res


@app.route('/get-subreddit-states')
def get_subreddit_states():
    token = request.cookies.get('access_token')
    subreddits = request.args.getlist('subreddits[]')
    with mp.Pool(5) as pool:
        active_states = list(
            pool.starmap(
                _is_subreddit_active, 
                zip(subreddits, itertools.repeat(token)))
        )
    return jsonify(active_states=active_states)


@app.route('/unsubscribe')
def unsubscribe_from_subreddit():
    pass
