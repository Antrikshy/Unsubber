'use strict';

const e = React.createElement;

class SubredditItem extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      loading: true
    };
    this.unsubscribe = this.unsubscribe.bind(this);
    this.subscribe = this.subscribe.bind(this);
  }

  unsubscribe() {
    axios.post('/unsubscribe', {
      subreddit: this.props.displayName
    }, {
      withCredentials: true
    }).then(res => {
      this.setState({
        unsubscribed: true
      });
    });
  }

  subscribe() {
    axios.post('/subscribe', {
      subreddit: this.props.displayName
    }, {
      withCredentials: true
    }).then(res => {
      this.setState({
        unsubscribed: false
      });
    });
  }

  render() {
    const state = this.props.isActive == undefined ? 'processing' : this.props.isActive ? 'active' : 'inactive';
    return e('div',
      {className: `subreddit-tile ${state} ${this.state.unsubscribed ? 'unsubscribed' : ''}`},
      [
        e('a', {href: `https://www.reddit.com/r/${this.props.displayName}`, target: '_blank'},
          [
            e('span', {}, 'r/'),
            e('strong', {className: 'subreddit-name'}, this.props.displayName),
          ]
        ),
        (state == 'inactive' && this.state.unsubscribed !== true
          ? e(
              'small',
              {className: 'unsubscribe-controls unsub-button', title: `Unsubscribe from ${this.props.displayName}`, onClick: this.unsubscribe},
              'leave')
          : null
        ),
        (this.state.unsubscribed === true
          ? e(
              'small',
              {className: 'unsubscribe-controls unsub-undo-button', title: `Subscribe to r/${this.props.displayName}`, onClick: this.subscribe},
              'undo')
          : null
        ),
        e('br'),
        e('span', {}, `${this.props.subscriberCount.toLocaleString()} subs.`),
        e('br'),
        e('span', {className: `label ${state}`}, state)
      ]
    );
  }
}

class SubredditList extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      activeStates: {},
      doneLoading: false
    };
    this.getSubredditStatesStaggered = this.getSubredditStatesStaggered.bind(this);
  }

  getSubredditStatesStaggered() {
    const _batchSize = 5;
    const _batchDelaySeconds = 5;
    const _expeditedBatchDelaySeconds = 2;
    const _superExpeditedBatchDelaySeconds = 0.5;  // Just to be safe, don't wanna get DDOS'd
    const allSubreddits = this.props.subreddits.map(sub => sub['display_name']);
    let slicer = 0;
    const updateActiveStates = newActiveStates => {
      this.setState({
        activeStates: {...this.state.activeStates, ...newActiveStates},
        doneLoading: Object.keys(this.state.activeStates).length + Object.keys(newActiveStates).length == this.props.subreddits.length
      });
    }
    // All this for Reddit rate limiting while using heuristics to make UX snappy
    setTimeout(function fetch() {
      const workingBatch = allSubreddits.slice(slicer, slicer + _batchSize);
      axios.get('/get-subreddit-states', { 
        params: { subreddits: workingBatch },
        withCredentials: true
      }).then(res => {
        // Boil down response to new active states and save them
        const newActiveStates = res.data['active_states'].reduce((acc, current) => Object.assign(acc, { 
          [current['subreddit']]: current['is_active']
        }), {});
        updateActiveStates(newActiveStates);
        // Check the number of subreddits checked that had cached states
        const numOfCachedSubs = res.data['active_states'].reduce((acc, current) => {
          return (current['cached']) ? acc + 1 : acc;
        }, 0);
        if (workingBatch.length == _batchSize) {
          slicer += _batchSize;
          // Default delay between requests
          let delayBeforeNextBatch = _batchDelaySeconds * 1000;
          if (numOfCachedSubs / _batchSize > 0.75) {
            // Slightly faster fetch next time if more than 75% were cached
            delayBeforeNextBatch = _expeditedBatchDelaySeconds * 1000;
          }
          if (numOfCachedSubs == _batchSize) {
            // Much faster fetch next time if all of them were cached
            delayBeforeNextBatch = _superExpeditedBatchDelaySeconds * 1000;
          }
          setTimeout(fetch, delayBeforeNextBatch);
        }
      });
    }, 0);
  }

  componentDidMount() {
    this.getSubredditStatesStaggered();
  }

  render() {
    const totalSubredditCount = this.props.subreddits.length;
    const inactiveSubredditCount = Object.values(this.state.activeStates).filter(s => !s).length;
    if (totalSubredditCount == 0) {
      return e('div', {}, [
        'You have not joined any subreddits yet. ',
        e('a', {href: 'https://www.reddit.com/subreddits', target: '_blank'}, 'Explore the catalog here'),
        '.'
      ]);
    }
    return e('div', {}, [
      e('div', {}, this.state.doneLoading
        ? [
          e('span', {}, `${totalSubredditCount} subreddits analyzed. ${inactiveSubredditCount} (~${Math.round(inactiveSubredditCount / totalSubredditCount * 100)}%) appear to be inactive.`),
          e('br'),
          e('br'),
        ] 
        : [
          e('span', {className: 'loading-indicator'}, 'Analyzing your subreddits. This could take a bit.'),
          e('br'),
          e('br'),
        ]
      ),
      e('div', {}, this.props.subreddits.map(sub => e(SubredditItem, 
        {
          key: sub['display_name'],
          displayName: sub['display_name'],
          subscriberCount: sub['subscribers'],
          isActive: this.state.activeStates[sub['display_name']]
        })
      ))
    ]);
  }
}

class App extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      subreddits: [],
      doneLoading: false
    };
  }

  componentDidMount() {
    axios.get('/my-subreddits', { withCredentials: true }).then(res => {
      this.setState({
        subreddits: res.data.subreddits,
        doneLoading: true
      });
    }).catch(err => {
      if (err.response && err.response.status == 401) {
        window.location.href = '/';
      }
    });
  }

  render() {
    return (this.state.doneLoading
      ? e(SubredditList, { subreddits: this.state.subreddits })
      : e('div', {className: 'loading-indicator'}, 'Fetching your subreddits.')
    )
  }
}

console.log("Running!")

const domContainer = document.querySelector('.app');
ReactDOM.render(e(App), domContainer);
