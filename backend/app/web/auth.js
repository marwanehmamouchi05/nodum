'use strict';
const byId = id => document.getElementById(id);
const params = new URLSearchParams(window.location.search);
let linking = window.location.pathname === '/ring/link';
let context;
let completed = false;
async function request(path, payload) {
  const response = await fetch(path, {
    method: payload === undefined ? 'GET' : 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', ...(context ? { 'X-CSRF-Token': context.csrf_token } : {}) },
    ...(payload === undefined ? {} : { body: JSON.stringify(payload) }),
  });
  const result = await response.json();
  if (!response.ok) {
    const error = new Error(typeof result.detail === 'string' ? result.detail : 'Request could not be completed.');
    error.status = response.status;
    throw error;
  }
  return result;
}
function render() {
  byId('login').hidden = !!context.user;
  byId('signed-in').hidden = !context.user;
  byId('claim').hidden = !linking || completed;
  byId('identity').textContent = context.user ? 'Signed in as ' + context.user.username : '';
  byId('heading').textContent = completed ? 'Ring connected' : linking ? 'Connect your Ring account' : 'Nodum account';
  byId('intro').textContent = linking ? 'Sign in, then confirm which Nodum account will own this Ring connection. The Ring link expires after 10 minutes.' : 'Return to the Nodum Integrations screen after signing in, or start account linking from Ring.';
}
async function run(work) {
  document.querySelectorAll('button').forEach(button => { button.disabled = true; });
  byId('message').textContent = 'Working…';
  try { await work(); } catch (error) {
    if (error.status === 401 || error.status === 403) {
      try { context = await request('/auth/session'); render(); } catch { /* Preserve the original error. */ }
    }
    byId('message').textContent = error.message;
  }
  finally { document.querySelectorAll('button').forEach(button => { button.disabled = false; }); }
}
byId('login').addEventListener('submit', event => {
  event.preventDefault();
  run(async () => {
    try { context = await request('/auth/login', { username: byId('username').value, password: byId('password').value }); }
    finally { byId('password').value = ''; }
    completed = false;
    render();
    byId('message').textContent = linking ? 'Confirm below to link Ring to this signed-in user.' : 'Signed in successfully.';
  });
});
byId('claim').addEventListener('click', () => run(async () => {
  const result = await request('/ring/link', { nonce: params.get('nonce'), time: Number(params.get('time')) });
  completed = true;
  linking = false;
  window.history.replaceState(null, '', '/auth/login');
  params.delete('nonce'); params.delete('time');
  render();
  byId('message').textContent = 'Ring connection completed for account ' + result.account_id + '. Return to Nodum Integrations to refresh the connection.';
}));
byId('logout').addEventListener('click', () => run(async () => {
  await request('/auth/logout', {});
  completed = false;
  context = await request('/auth/session');
  render(); byId('message').textContent = 'Signed out.';
}));
run(async () => {
  context = await request('/auth/session');
  render(); byId('message').textContent = context.user ? 'Your session is ready.' : 'Sign in to continue. Your Ring parameters remain on this page.';
});
