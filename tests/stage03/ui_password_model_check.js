// Playwriter UI check for ContactAccess (review finding B6): after a new password is saved through the form, the plain
// value must not remain in the client model. Run after `python3 tests/stage03/ui_fixture.py create` and
// `state.who = "access"` + tests/stage03/ui_login.js: `playwriter -s <id> -f tests/stage03/ui_password_model_check.js`.
const fs = await import('node:fs');
const fixture = JSON.parse(fs.readFileSync('/data/itvolga/espo-private/stand/evidence/stage03/ui-fixture.json', 'utf-8'));
await state.page.goto('http://crm.itvolga.test/#ContactAccess/view/' + fixture.contactAccess, { waitUntil: 'domcontentloaded' });
await state.page.getByText('Показать пароль').first().waitFor({ timeout: 20000 });
await state.page.evaluate(async () => {
  const V = await Espo.loader.requirePromise('itvolga:views/contact-access/fields/password');
  const proto = (V.default || V).prototype;
  if (!proto.__patched) {
    const orig = proto.afterRender;
    proto.afterRender = function (...args) { window.__caModel = this.model; return orig.apply(this, args); };
    proto.__patched = true;
  }
});
await state.page.locator('role=button[name="Редактировать"i]').first().click();
await state.page.locator('.cell[data-name="anydeskPassword"] [data-action="change"]').waitFor({ timeout: 10000 });
await state.page.locator('.cell[data-name="anydeskPassword"] [data-action="change"]').click();
await state.page.evaluate(() => { const i = document.querySelector('.cell[data-name="anydeskPassword"] input'); i.value = 'exampleB6Value4'; i.dispatchEvent(new Event('change', { bubbles: true })); });
await state.page.locator('role=button[name="Сохранить"i]').first().click();
await state.page.getByText('Показать пароль').first().waitFor({ timeout: 10000 });
await state.page.waitForTimeout(500);
const res = await state.page.evaluate(() => [window.__caModel].filter(Boolean).map((m) => ({
  has: m.has('anydeskPassword'),
  prev: !!(m._previousAttributes && 'anydeskPassword' in m._previousAttributes && m._previousAttributes.anydeskPassword),
  plainAnywhere: JSON.stringify(m.attributes).includes('exampleB6Value4') || JSON.stringify(m._previousAttributes || {}).includes('exampleB6Value4'),
})));
console.log('models:', JSON.stringify(res));
