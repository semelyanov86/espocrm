// Playwriter scenario 2 (stage 05.1): a tabular report on Invoice built in the builder, then «Сохранить и показать».
// Needs tests/stage05_1/ui/helpers.js run first in the session. state.reportName, state.rowLimit, state.statuses
// (status values for the «in list» condition).
const page = state.page;
const ui = state.ui;
await page.goto('http://crm.itvolga.test/#Report/create', { waitUntil: 'domcontentloaded' });
await page.waitForSelector('.field[data-name="entityType"] select', { state: 'attached', timeout: 15000 });
await page.waitForTimeout(1000);
await ui.setInput(page, '.field[data-name="name"] input', state.reportName || 'UI tabular');
await ui.setSearch(page, '.field[data-name="entityType"] select', 'Invoice');
await page.waitForTimeout(1500);
await ui.tab(page, 'Колонки и сортировка');
for (const ref of ['number', 'account', 'account.name', 'dateInvoiced', 'status', 'grandTotal']) {
  await ui.addField(page, 'columns', ref);
}
await page.evaluate(() => document.querySelector('.field[data-name="sorting"] button[data-action="addItem"]').click());
await page.waitForTimeout(400);
await ui.setSelect(page, '.field[data-name="sorting"] select[data-key="column"]', 'grandTotal');
await ui.setSelect(page, '.field[data-name="sorting"] select[data-key="direction"]', 'desc');
await ui.setInput(page, '.field[data-name="rowLimit"] input', String(state.rowLimit || 5));
await ui.tab(page, 'Фильтры');
await ui.addCondition(page, 'status');
await ui.addCondition(page, 'dateInvoiced');
console.log('builder filled');
