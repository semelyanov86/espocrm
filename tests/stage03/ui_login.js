// Playwriter helper for the UI scenarios: `state.who = "admin"|"deputy"|"access"` (stage 03) or another user of a
// fixture with `state.usersEnv = <its ui-users.env>` (stage 04.2: "director", "fdeputy"), then
// `playwriter -s <id> -f tests/stage03/ui_login.js`. Reads passwords from the private stand files (never printed).
// Logs into the local stand; credentials are read from private files and never printed.
const fs = await import('node:fs');
function readEnv(path) {
  const out = {};
  for (const line of fs.readFileSync(path, 'utf-8').split('\n')) {
    const i = line.indexOf('=');
    if (i > 0 && !line.trim().startsWith('#')) out[line.slice(0, i).trim()] = line.slice(i + 1).trim().replace(/^['"]|['"]$/g, '');
  }
  return out;
}
const who = state.who || 'admin';
let user, pw;
if (who === 'admin') {
  const e = readEnv('/data/itvolga/espo-private/stand/local.env');
  user = e.ESPO_ADMIN_USERNAME; pw = e.ESPO_ADMIN_PASSWORD;
} else {
  const e = readEnv(state.usersEnv || '/data/itvolga/espo-private/stand/evidence/stage03/ui-users.env');
  user = e[`UI_${who.toUpperCase()}_USERNAME`]; pw = e[`UI_${who.toUpperCase()}_PASSWORD`];
}
if (!state.page || state.page.isClosed()) {
  state.page = context.pages().findLast((p) => p.url() === 'about:blank') ?? (await context.newPage());
}
if (!state.page.url().startsWith('http://crm.itvolga.test')) {
  await state.page.goto('http://crm.itvolga.test/', { waitUntil: 'domcontentloaded' });
}
// sign out by removing only this site's cookies (no reload of the running app, no other domains touched)
const cdp = await getCDPSession({ page: state.page });
const { cookies } = await cdp.send('Network.getCookies', { urls: ['http://crm.itvolga.test/'] });
for (const ck of cookies) await cdp.send('Network.deleteCookies', { name: ck.name, domain: ck.domain, path: ck.path });
await state.page.goto('http://crm.itvolga.test/?_=' + Date.now(), { waitUntil: 'domcontentloaded' });
await state.page.waitForSelector('#field-userName', { timeout: 15000 });
// focusing the inputs lets a browser password manager inject its UI and detach the tab: set values directly
await state.page.evaluate(([u, p]) => {
  document.querySelector('#field-userName').value = u;
  document.querySelector('#field-password').value = p;
}, [user, pw]);
await state.page.locator('#btn-login').click();
await state.page.getByRole('link', { name: /Главная/ }).first().waitFor({ timeout: 15000 });
console.log('logged in as', who, state.page.url());
