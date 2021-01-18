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
      {className: `subreddit-tile ${this.state.unsubscribed ? 'unsubscribed' : ''}`},
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
      activeStates: {}
    };
    this.getSubredditStatesStaggered = this.getSubredditStatesStaggered.bind(this);
  }

  getSubredditStatesStaggered() {
    const _batchSize = 5;
    const _batchDelaySeconds = 5;
    const _expeditedBatchDelaySeconds = 2;
    const allSubreddits = this.props.subreddits.map(sub => sub['display_name']);
    let slicer = 0;
    const updateActiveStates = newActiveStates => {
      this.setState({
        activeStates: {...this.state.activeStates, ...newActiveStates}
      });
    }
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
          const delayBeforeNextBatch =
            (numOfCachedSubs / _batchSize > 0.75) 
              ? _expeditedBatchDelaySeconds * 1000 
              : _batchDelaySeconds * 1000;
          setTimeout(fetch, delayBeforeNextBatch);
        }
      });
    }, 0);
  }

  componentDidUpdate(prevProps) {
    if (this.props.subreddits !== prevProps.subreddits) {
      this.getSubredditStatesStaggered();
    }
  }

  render() {
    return this.props.subreddits.map(sub => e(SubredditItem, 
      {
        key: sub['display_name'],
        displayName: sub['display_name'],
        subscriberCount: sub['subscribers'],
        isActive: this.state.activeStates[sub['display_name']]
      })
    );
  }
}

class App extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      subreddits: []
    };
  }

  componentDidMount() {
    axios.get('/my-subreddits', { withCredentials: true }).then(res => {
      this.setState({
        subreddits: res.data.subreddits
      });
    }).catch(err => {
      if (err.response && err.response.status == 401) {
        window.location.href = "/";
      }
    });
  }

  render() {
    return e(SubredditList, { subreddits: this.state.subreddits });
  }
}

console.log("Running!")

const domContainer = document.querySelector('.app');
ReactDOM.render(e(App), domContainer);
