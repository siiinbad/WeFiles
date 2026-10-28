(() => {
  const initialHistory = document.querySelector('#conversation .messages-history');
  if (initialHistory && !location.search.includes('page=')) initialHistory.scrollTop = initialHistory.scrollHeight;
  let chatPosition = {follow: true, top: 0};
  document.body.addEventListener('htmx:configRequest', event => {
    if (event.detail.elt.id === 'conversation') {
      const history = event.detail.elt.querySelector('.messages-history');
      if (history) {
        event.detail.headers['X-WeFiles-Latest'] = history.dataset.latestMessage;
        event.detail.headers['X-WeFiles-Count'] = history.dataset.messageCount;
        chatPosition = {follow: history.scrollHeight - history.scrollTop - history.clientHeight < 80, top: history.scrollTop};
      }
    }
  });
  document.body.addEventListener('htmx:afterSwap', event => {
    if (event.target.id === 'conversation') {
      const history = event.target.querySelector('.messages-history');
      if (history) history.scrollTop = chatPosition.follow ? history.scrollHeight : chatPosition.top;
    }
  });
})();
