// Helpers of the stage 05.1 Playwriter scenarios: values are set through the selectize API and DOM change events — a
// click into a search input of a background tab can detach it from the extension (CLAUDE.md, Playwriter notes).
state.ui = {
  async setSearch(page, selector, value) {
    await page.evaluate(([s, v]) => {
      const el = document.querySelector(s);
      if (!el) throw new Error('no element: ' + s);
      if (el.selectize) {
        el.selectize.setValue(v);
      } else {
        el.value = v; el.dispatchEvent(new Event('change', {bubbles: true}));
      }
    }, [selector, value]);
    await page.waitForTimeout(400);
  },
  async setSelect(page, selector, value) {
    await page.evaluate(([s, v]) => {
      const el = document.querySelector(s);
      if (!el) throw new Error('no element: ' + s);
      el.value = v; el.dispatchEvent(new Event('change', {bubbles: true}));
    }, [selector, value]);
    await page.waitForTimeout(300);
  },
  async setInput(page, selector, value) {
    await page.evaluate(([s, v]) => {
      const el = document.querySelector(s);
      if (!el) throw new Error('no element: ' + s);
      el.value = v; el.dispatchEvent(new Event('change', {bubbles: true}));
    }, [selector, value]);
    await page.waitForTimeout(200);
  },
  async tab(page, name) {
    await page.evaluate((n) => [...document.querySelectorAll('.middle-tabs > button')]
      .find(b => b.textContent.trim() === n).click(), name);
    await page.waitForTimeout(500);
  },
  async addField(page, field, ref) {
    await this.setSearch(page, `.field[data-name="${field}"] select[data-role="picker"]`, ref);
    await page.evaluate((f) => document.querySelector(`.field[data-name="${f}"] button[data-action="addItem"]`).click(), field);
    await page.waitForTimeout(500);
  },
  async addCondition(page, ref) {
    await this.setSearch(page, '.field[data-name="filters"] select[data-role="picker"]', ref);
    await page.evaluate(() => document.querySelector('.field[data-name="filters"] button[data-action="addCondition"]').click());
    await page.waitForTimeout(1500);
  },
};
console.log('ui helpers ready');
