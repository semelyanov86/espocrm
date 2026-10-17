// Stage 08 browser check of the rehearsal (docs/migration/rehearsal.md): Playwriter script run in a session created
// in the private evidence directory, after tests/stage03/ui_login.js. The stand holds real imported data, so the
// script prints only flags, counts and response codes — never field values; screenshots stay in that directory.
//
//   state.part = "admin"    → client, invoice → act → payment → PDF, ticket and client, document and download, call
//                             and its recording (state.who = "admin")
//   state.part = "director" → the recording plays for another user who reads the call (state.who = "director")
//   state.part = "manager"  → a user who cannot read the call gets neither the call nor its recording
//
// Record ids: <evidence>/ui-records.json (tests/stage08/ui_fixture.py create); <evidence>/ui-document.sha256 — sha256 of
// the document's file in the stand storage (the import checked it against the snapshot), compared, never printed.
const fs = await import('node:fs');
const crypto = await import('node:crypto');
const DIR = '/data/itvolga/espo-private/stand/evidence/stage08';
const ids = JSON.parse(fs.readFileSync(`${DIR}/ui-records.json`, 'utf-8'));
const expectSha = fs.existsSync(`${DIR}/ui-document.sha256`) ?
  fs.readFileSync(`${DIR}/ui-document.sha256`, 'utf-8').trim().slice(0, 64) : '';
const page = state.page;
const out = {};

async function shot(name) {
  const path = `${DIR}/${state.part}-${name}.png`;
  await page.screenshot({ path, scale: 'css' });
  fs.chmodSync(path, 0o600);
}

async function closeUpdatedModal() {
  // after task model:apply the core asks to reload the application; close it before clicking
  await page.evaluate(() => {
    for (const m of document.querySelectorAll('.modal')) {
      if (getComputedStyle(m).display !== 'none') m.querySelector('[data-name="cancel"], .close')?.click();
    }
  });
}

async function open(scope, id) {
  await page.evaluate(([s, i]) => { location.hash = `#${s}/view/${i}`; }, [scope, id]);
  await page.waitForFunction(([s, i]) => {
    const rec = document.querySelector('.record[data-scope], .detail');
    return location.hash === `#${s}/view/${i}` && document.querySelector('.detail .field[data-name]') && rec;
  }, [scope, id], { timeout: 30000 });
  await page.waitForTimeout(1500); // bottom panels load after the record
  await closeUpdatedModal();
}

const flags = (code) => page.evaluate(code);
const filled = (name) => `!!document.querySelector('.detail .field[data-name="${name}"]')?.textContent.trim()`;
const linkTo = (scope, id) => `!!document.querySelector('.detail a[href="#${scope}/view/${id}"]')`;
const panelLinks = (panel, scope, id) =>
  `!!document.querySelector('.panel[data-name="${panel}"] a[href="#${scope}/view/${id}"]')`;
const panelRows = (panel) => `document.querySelectorAll('.panel[data-name="${panel}"] tr[data-id]').length`;

async function fetchInfo(url, headers = {}) {
  return page.evaluate(async ([u, h]) => {
    const r = await fetch(u, { headers: h, credentials: 'same-origin' });
    const buf = new Uint8Array(await r.arrayBuffer());
    return { status: r.status, type: (r.headers.get('Content-Type') || '').split(';')[0], size: buf.length,
             magic: String.fromCharCode(...buf.slice(0, 4)), bytes: Array.from(buf) };
  }, [url, headers]);
}

async function pdf(entityType, id) {
  const r = await fetchInfo(`?entryPoint=itvolgaPrint&entityType=${entityType}&id=${id}`);
  const path = `${DIR}/${state.part}-${entityType}.pdf`;
  fs.writeFileSync(path, Buffer.from(r.bytes), { mode: 0o600 });
  return { status: r.status, type: r.type, pdf: r.magic === '%PDF', size: r.size > 1000 };
}

async function recording(id, range = true) {
  const r = await fetchInfo(`?entryPoint=itvolgaRecording&id=${id}`, range ? { Range: 'bytes=0-15' } : {});
  return { status: r.status, type: r.type, riff: r.magic === 'RIFF' };
}

if (state.part === 'admin') {
  await open('Account', ids.account);
  out.account = await flags(`({name: ${filled('name')}, contacts: ${panelRows('contacts')} > 0,
    invoices: ${panelRows('cInvoices')} > 0, acts: ${panelRows('cActs')} > 0, payments: ${panelRows('cPayments')} > 0})`);
  await shot('account');

  await open('Invoice', ids.invoice);
  out.invoice = await flags(`({number: ${filled('number')}, grandTotal: ${filled('grandTotal')},
    status: ${filled('status')}, account: ${linkTo('Account', ids.account)}, act: ${linkTo('Act', ids.act)},
    items: document.querySelectorAll('.detail .field[data-name="itemList"] tbody tr').length > 0})`);
  out.invoice.print = await pdf('Invoice', ids.invoice);
  await shot('invoice');

  await page.locator(`.detail a[href="#Act/view/${ids.act}"]`).first().click(); // invoice → act through the UI
  await page.waitForFunction((i) => location.hash === `#Act/view/${i}` &&
    document.querySelector('.detail .field[data-name="number"]'), ids.act, { timeout: 30000 });
  await page.waitForTimeout(1500);
  out.act = await flags(`({number: ${filled('number')}, grandTotal: ${filled('grandTotal')},
    items: document.querySelectorAll('.detail .field[data-name="itemList"] tbody tr').length > 0,
    invoiceInPanel: !!document.querySelector('a[href="#Invoice/view/${ids.invoice}"]')})`);
  out.act.print = await pdf('Act', ids.act);
  await shot('act');

  await open('Invoice', ids.invoice); // invoice → allocation → payment through the links of the cards
  out.invoice.allocationInPanel = await flags(panelLinks('paymentAllocations', 'PaymentAllocation', ids.allocation));
  await page.locator(`.panel[data-name="paymentAllocations"] a[href="#PaymentAllocation/view/${ids.allocation}"]`)
    .first().click();
  await page.waitForFunction((i) => location.hash === `#PaymentAllocation/view/${i}`, ids.allocation, { timeout: 30000 });
  await page.waitForTimeout(1500);
  out.allocation = await flags(`({invoice: ${linkTo('Invoice', ids.invoice)}, payment: ${linkTo('Payment', ids.payment)},
    amount: ${filled('amount')}})`);
  await page.locator(`.detail a[href="#Payment/view/${ids.payment}"]`).first().click();
  await page.waitForFunction((i) => location.hash === `#Payment/view/${i}` &&
    document.querySelector('.detail .field[data-name="amount"]'), ids.payment, { timeout: 30000 });
  await page.waitForTimeout(1500);
  out.payment = await flags(`({number: ${filled('number')}, amount: ${filled('amount')},
    direction: ${filled('direction')},
    allocationToInvoice: !!document.querySelector('a[href="#Invoice/view/${ids.invoice}"]')})`);
  out.payment.print = await pdf('Payment', ids.payment);
  await shot('payment');

  await open('Case', ids.case); // ticket → client and back
  out.case = await flags(`({name: ${filled('name')}, status: ${filled('status')},
    account: ${linkTo('Account', ids.caseAccount)}})`);
  await shot('case');
  await page.locator(`.detail a[href="#Account/view/${ids.caseAccount}"]`).first().click();
  await page.waitForFunction((i) => location.hash === `#Account/view/${i}`, ids.caseAccount, { timeout: 30000 });
  await page.waitForTimeout(2500);
  out.case.caseInClientPanel = await flags(panelLinks('cases', 'Case', ids.case));
  await shot('case-account');

  await open('Document', ids.document);
  const href = await flags(`document.querySelector('.detail .field[data-name="file"] a[href*="entryPoint=download"]')
    ?.getAttribute('href') || ''`);
  const file = href ? await fetchInfo(href) : { status: 0, bytes: [] };
  out.document = { name: await flags(filled('name')), downloadLink: !!href, status: file.status,
    sameBytes: !!expectSha && crypto.createHash('sha256').update(Buffer.from(file.bytes)).digest('hex') === expectSha };
  await shot('document');
}

if (['admin', 'director'].includes(state.part)) {
  await open('Call', ids.call);
  out.call = await flags(`({cdrSource: ${filled('cCdrSource')}, linkedId: ${filled('cAsteriskLinkedId')},
    player: !!document.querySelector('.detail .field[data-name="cRecording"] audio'),
    dateStart: ${filled('dateStart')}})`);
  out.call.recording = await recording(ids.call);
  out.call.recordingWhole = (await recording(ids.call, false)).status;
  await shot('call');
}

if (state.part === 'manager') {
  out.callApi = await page.evaluate(async (i) => (await fetch(`api/v1/Call/${i}`)).status, ids.call);
  out.recording = await recording(ids.call);
  await page.evaluate((i) => { location.hash = `#Call/view/${i}`; }, ids.call);
  await page.waitForTimeout(3000);
  out.callPage = await flags(`({fields: !!document.querySelector('.detail .field[data-name="cRecording"]'),
    player: !!document.querySelector('audio')})`);
  await shot('call-denied');
}

console.log(JSON.stringify(out));
const logs = await getLatestLogs({ page, sinceLastCall: true, search: /error|exception/i });
console.log('error log lines:', logs.length);
