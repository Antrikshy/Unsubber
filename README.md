![](https://github.com/Antrikshy/Unsubber/blob/main/src/static/Unsubber-Logo.png)

A simple web app that lets you log in with your Reddit credentials, analyzes your list of subreddit subscriptions, and helps you clean out inactive subreddits that you may be subscribed to.

It respects and attempts to work around the Reddit API rate limitations by internally caching analyzed subreddit activity states.

**[Visit Unsubber](https://unsubber.antrikshy.com)**

Contributing
------------

To fully test this web app, you'll need a Reddit account, which you will use to temporarily register an application as a developer. You can always clean this up later.

In addition to that, a Python 3 installation is required.

1. Create a dummy application [through your Reddit acccount](https://www.reddit.com/prefs/apps/) and set its "redirect uri" to "http://127.0.0.1:5000/oauth-redirect". Fill out the other fields to whatever you want.
2. Copy this application's ID and secret into a new file called `config.txt`. See `config.example` for more info. Place this file at the top level of this repo (alongide `src`).
3. While not required, I recommend using [virtualenv](https://virtualenv.pypa.io/en/latest/) or a similar Python environment manager. If you're new to Python, see [my quick primer](https://antrikshy.com/code/virtualenv-quick-practical-explanation-beginners) on virtualenv. Either way, install this project's dependencies from `requirements.txt` by running `pip3 install -r requirements.txt`.
4. With TCP port 5000 clear of anything else you may have running, run `dev.sh`. This should bring up the Flask development server with auto-reloading.
5. Navigate to `127.0.0.1:5000` in a browser. If everything is set up correctly, you should be able to log into the site with your actual Reddit credentials.

I expect this to be a one-and-done project, but pull requests are always welcome!
