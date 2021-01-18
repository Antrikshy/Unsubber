import os
import time
import itertools
import multiprocessing as mp
import sqlite3
from datetime import datetime

from flask import Flask, request, render_template, make_response, jsonify, redirect
import requests


app = Flask(__name__)

_REDDIT_ROOT_URL = 'https://www.reddit.com'
_REDDIT_OAUTH_ROOT_URL = 'https://oauth.reddit.com'
_REDDIT_AUTH_URL_TEMPLATE = _REDDIT_ROOT_URL + \
    '/api/v1/authorize?client_id={}&response_type={}&state={}&redirect_uri={}&duration={}&scope={}'
_APP_CLIENT_ID = os.environ['UNSUBBER_CLIENT_ID']
_APP_CLIENT_SECRET = os.environ['UNSUBBER_CLIENT_SECRET']
_APP_REDIRECT_URL = 'http://unsubber.antrikshy.com/oauth-redirect'
_APP_HTTP_REQUEST_HEADER = {'User-Agent': 'Unsubber by u/Antrikshy'}
_CACHE_DB_FILE_NAME = './subreddit_activity.db'
_CACHE_DB_TABLE_NAME = 'active_subreddits'

conn = sqlite3.connect(_CACHE_DB_FILE_NAME)
cursor = conn.cursor()
cursor.execute(f'''CREATE TABLE IF NOT EXISTS {_CACHE_DB_TABLE_NAME} (
    subreddit TEXT PRIMARY KEY,
    is_active INTEGER NOT NULL,
    last_checked TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
)''')
conn.commit()
conn.close()


def _generate_reddit_oauth_url():
    return _REDDIT_AUTH_URL_TEMPLATE.format(
        _APP_CLIENT_ID,
        'code',
        'login',
        _APP_REDIRECT_URL,
        'temporary',
        'mysubreddits,subscribe,read'
    )


def _generate_reddit_auth_code_payload(code):
    return {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': _APP_REDIRECT_URL
    }


def _get_all_user_subreddits(access_token):
    after = ''
    subreddits = []
    while after is not None:
        url = f'{_REDDIT_OAUTH_ROOT_URL}/subreddits/mine/subscriber?raw_json=1&limit=100&after={after}'
        res = requests.get(url, headers={**_APP_HTTP_REQUEST_HEADER, 'Authorization': f'Bearer {access_token}'})
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
    # return [
    #     {
    #         'display_name': 'blog',
    #         'subscribers': 12345
    #     },
    #     {
    #         'display_name': 'redesign',
    #         'subscribers': 12345
    #     },
    #     {
    #         'display_name': 'wolframalpha',
    #         'subscribers': 12345
    #     },
    #     {
    #         'display_name': 'announcements',
    #         'subscribers': 12345
    #     }
    # ]


def _is_subreddit_active(subreddit, access_token):
    conn = sqlite3.connect(_CACHE_DB_FILE_NAME, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    # Check cache for this subreddit
    row = cursor.execute(f'SELECT * from {_CACHE_DB_TABLE_NAME} WHERE subreddit=?', [subreddit]).fetchone()
    subreddit_is_active = True
    cached = False
    if row is not None and (datetime.now() - dict(row)['last_checked']).days <= 21:
        # If the sub was recently checked
        subreddit_is_active = dict(row)['is_active'] == 1
        cached = True
    else:
        # If the sub is new or was checked some time ago
        # Requesting a list of newest posts, with the limit set to Reddit's maximum of 100
        url = f'{_REDDIT_OAUTH_ROOT_URL}/r/{subreddit}/new.json?limit=100'
        res = requests.get(url, headers={**_APP_HTTP_REQUEST_HEADER, 'Authorization': f'Bearer {access_token}'})
        if res.status_code != 200:
            res.raise_for_status()
        j_res = res.json()
        # Reading subreddit and post metadata
        r_subreddit_data = j_res['data']['children']
        if len(r_subreddit_data) == 0:
            subreddit_is_active = False
        else:
            r_subreddit_subscribers = r_subreddit_data[0]['data']['subreddit_subscribers']
            r_post_created_collation = list(map(lambda post: post['data']['created'], r_subreddit_data))
            # Computing active state (aka #TheAlgorithm)
            # Subreddit is deemed inactive...
            # ... if it has under 300 subscribers
            if r_subreddit_subscribers < 300:
                subreddit_is_active = False
            # ... or if the newest post is over 2 months old (should weed out very inactive ones)
            elif time.time() - r_post_created_collation[0] > 5256000:
                subreddit_is_active = False
            # ... or...
            else:
                # ... Loop through the newest 100 posts, or up to the last two months,
                # whichever comes first, and deem inactive if there were fewer than 15 posts.
                num_recent_posts = 0
                for timestamp in r_post_created_collation:
                    if time.time() - timestamp < 5256000:
                        num_recent_posts += 1
                    else:
                        break
                if num_recent_posts < 15:
                    subreddit_is_active = False
        cursor.execute(f'INSERT INTO {_CACHE_DB_TABLE_NAME} VALUES (?, ?, CURRENT_TIMESTAMP)', [subreddit, 1 if subreddit_is_active else 0])
        conn.commit()
    conn.close()
    return {'is_active': subreddit_is_active, 'subreddit': subreddit, 'cached': cached}


# ------------------------------------------
# -------- PAGE RENDERING AND LOGIN --------
# ------------------------------------------

@app.route('/', methods=['GET'])
def render_login():
    return render_template('login.html')


@app.route('/login', methods=['GET'])
def redirect_to_login():
    return redirect(_generate_reddit_oauth_url())


@app.route('/unsub', methods=['GET'])
def render_main_app():
    token = request.cookies.get('access_token')
    if token is None:
        return redirect('/')
    return render_template('main.html')


@app.route('/oauth-redirect', methods=['GET'])
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

@app.route('/my-subreddits', methods=['GET'])
def get_subreddits():
    token = request.cookies.get('access_token')
    try:
        subreddits = _get_all_user_subreddits(token)
        return jsonify(subreddits=subreddits)
    except requests.exceptions.HTTPError as e:
        res = make_response()
        res.status_code = e.response.status_code
        return res


@app.route('/get-subreddit-states', methods=['GET'])
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


@app.route('/unsubscribe', methods=['POST'])
def unsubscribe_from_subreddit():
    token = request.cookies.get('access_token')
    subreddit = request.json['subreddit']
    url = f'{_REDDIT_OAUTH_ROOT_URL}/api/subscribe'
    res = requests.post(
        url,
        data={'action': 'unsub', 'sr_name': subreddit},
        headers={**_APP_HTTP_REQUEST_HEADER, 'Authorization': f'Bearer {token}'}
    )
    if res.status_code != 200:
        res.raise_for_status()
    else:
        return 'SUCCESS', 200


@app.route('/subscribe', methods=['POST'])
def subscribe_to_subreddit():
    token = request.cookies.get('access_token')
    subreddit = request.json['subreddit']
    url = f'{_REDDIT_OAUTH_ROOT_URL}/api/subscribe'
    res = requests.post(
        url,
        data={'action': 'sub', 'sr_name': subreddit, 'skip_initial_defaults': True},
        headers={**_APP_HTTP_REQUEST_HEADER, 'Authorization': f'Bearer {token}'}
    )
    if res.status_code != 200:
        res.raise_for_status()
    else:
        return 'SUCCESS', 200
