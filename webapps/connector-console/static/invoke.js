async function init() {
  try {
    await loadLocalKeys('user-id');
  } catch(e) {
    showResult(e);
  }
}

async function invokeResource() {
  try {
    const data = await api('/api/console/invoke', {
      method: 'POST',
      body: JSON.stringify({
        resource_id: val('resource-id'),
        user_id: val('user-id'),
        method: val('method'),
        query_params: val('query-params'),
        body: document.getElementById('body').value,
      }),
    });
    showResult(data);
  } catch(e) {
    showResult(e);
  }
}

init();
