/**
 * Line items of a finance document (Quote, SalesOrder): the table is edited in the document form and saved with it
 * by one request (`itemList`, owner decision 2026-10-01). Values stay decimal strings; amounts and totals come from
 * the server only — saved values, or a preview of the same calculation while the form is edited
 * (POST FinanceDocument/:entityType/calculate). The browser does no arithmetic with money.
 */
define('itvolga:views/finance/fields/item-list', ['views/fields/base', 'itvolga:finance/decimal-text'],
    (BaseFieldView, DecimalText) => {

    const INPUTS = ['quantity', 'unitPrice', 'discountAmount', 'discountPercent', 'taxRate', 'purchaseCost'];
    const SENT = ['id', 'productId', 'productName', 'description', ...INPUTS];
    const HEADER = ['taxMode', 'discountAmount', 'discountPercent', 'shippingAmount', 'adjustment'];
    const PREVIEW_DELAY = 400;

    const tableHead = `
        <thead><tr style="white-space: nowrap;">
            <th style="width: 3em;">{{labels.order}}</th>
            <th style="min-width: 15em;">{{labels.product}}</th>
            <th style="min-width: 11em;">{{labels.description}}</th>
            <th class="text-right" style="width: 8em;">{{labels.quantity}}</th>
            <th class="text-right" style="width: 10em;">{{labels.unitPrice}}</th>
            <th class="text-right" style="width: 11em;">{{labels.discount}}</th>
            <th class="text-right" style="width: 6em;">{{labels.taxRate}}</th>
            {{#if showCost}}<th class="text-right" style="width: 10em;">{{labels.purchaseCost}}</th>{{/if}}
            <th class="text-right" style="width: 10em;">{{labels.amount}}</th>
            {{#if isEdit}}<th style="width: 7em;"></th>{{/if}}
        </tr></thead>`;

    return class extends BaseFieldView {

        listTemplateContent = ''

        detailTemplateContent = `
            {{#if isEmpty}}<span class="none-value">{{translate 'None'}}</span>{{else}}
            <div class="itv-item-list" style="overflow-x: auto;">
            <table class="table table-bordered-inside" style="margin-bottom: 0;">${tableHead}
            <tbody>{{#each lines}}<tr>
                <td>{{number}}</td>
                <td>{{#if productId}}<a href="#Product/view/{{productId}}">{{productName}}</a>{{/if}}</td>
                <td style="white-space: pre-wrap;">{{description}}</td>
                <td class="text-right">{{quantity}}</td>
                <td class="text-right">{{unitPrice}}</td>
                <td class="text-right">{{discountText}}</td>
                <td class="text-right {{#if hasTax}}text-warning{{/if}}">{{taxRate}}</td>
                {{#if ../showCost}}<td class="text-right">{{purchaseCost}}</td>{{/if}}
                <td class="text-right">{{amount}}</td>
            </tr>{{/each}}</tbody></table></div>{{/if}}
            {{#if sourceNote}}<div class="text-muted small" style="margin-top: 4px;">{{sourceNote}}</div>{{/if}}`

        editTemplateContent = `
            <div class="itv-item-list" style="overflow-x: auto;">
            <table class="table table-bordered-inside" style="margin-bottom: 4px; min-width: 70em;">${tableHead}
            <tbody>{{#each lines}}<tr data-index="{{index}}">
                <td>{{number}}</td>
                <td><div class="input-group input-group-sm {{#if invalid.product}}has-error{{/if}}">
                    <input type="text" class="form-control" value="{{productName}}" title="{{productName}}" readonly>
                    <span class="input-group-btn"><button type="button" class="btn btn-default btn-icon"
                        data-action="selectProduct" data-index="{{index}}" title="{{../labels.selectProduct}}">
                        <span class="fas fa-angle-up"></span></button></span></div></td>
                <td><textarea class="form-control input-sm" rows="1" data-field="description">{{description}}</textarea></td>
                <td class="{{#if invalid.quantity}}has-error{{/if}}"><input type="text" inputmode="decimal"
                    class="form-control input-sm text-right" data-field="quantity" value="{{quantity}}"></td>
                <td class="{{#if invalid.unitPrice}}has-error{{/if}}"><input type="text" inputmode="decimal"
                    class="form-control input-sm text-right" data-field="unitPrice" value="{{unitPrice}}"></td>
                <td class="{{#if invalid.discount}}has-error{{/if}}"><div class="input-group input-group-sm">
                    <input type="text" inputmode="decimal" class="form-control text-right" data-field="discount"
                        value="{{discount}}">
                    <span class="input-group-btn" style="width: 3.5em;"><select class="form-control" data-field="discountType">
                        <option value="amount" {{#unless discountIsPercent}}selected{{/unless}}>{{../labels.discountAmount}}</option>
                        <option value="percent" {{#if discountIsPercent}}selected{{/if}}>{{../labels.discountPercent}}</option>
                    </select></span></div></td>
                <td class="{{#if invalid.taxRate}}has-error{{/if}} {{#if hasTax}}has-warning{{/if}}"><input type="text"
                    inputmode="decimal" class="form-control input-sm text-right" data-field="taxRate" value="{{taxRate}}"></td>
                {{#if ../showCost}}<td class="{{#if invalid.purchaseCost}}has-error{{/if}}"><input type="text"
                    inputmode="decimal" class="form-control input-sm text-right" data-field="purchaseCost"
                    value="{{purchaseCost}}"></td>{{/if}}
                <td class="text-right" data-role="amount" data-index="{{index}}">{{amount}}</td>
                <td class="text-nowrap">
                    <button type="button" class="btn btn-link btn-sm btn-icon" data-action="moveLine" data-index="{{index}}"
                        data-step="-1" title="{{../labels.moveUp}}" {{#if isFirst}}disabled{{/if}}><span class="fas fa-arrow-up"></span></button>
                    <button type="button" class="btn btn-link btn-sm btn-icon" data-action="moveLine" data-index="{{index}}"
                        data-step="1" title="{{../labels.moveDown}}" {{#if isLast}}disabled{{/if}}><span class="fas fa-arrow-down"></span></button>
                    <button type="button" class="btn btn-link btn-sm btn-icon" data-action="removeLine" data-index="{{index}}"
                        title="{{../labels.removeLine}}"><span class="fas fa-times"></span></button>
                </td>
            </tr>{{/each}}</tbody></table></div>
            <button type="button" class="btn btn-default btn-sm" data-action="addLine">
                <span class="fas fa-plus fa-sm"></span> {{labels.addLine}}</button>
            <label class="checkbox-inline small" style="margin-left: 12px;">
                <input type="checkbox" data-action="toggleCost" {{#if showCost}}checked{{/if}}> {{labels.purchaseCost}}</label>
            <div class="small" data-role="preview" style="margin-top: 6px;"></div>`

        setup() {
            super.setup();

            this.decimalMark = (this.getPreferences().has('decimalMark') ?
                this.getPreferences().get('decimalMark') : this.getConfig().get('decimalMark')) || '.';
            this.thousandSeparator = (this.getPreferences().has('thousandSeparator') ?
                this.getPreferences().get('thousandSeparator') : this.getConfig().get('thousandSeparator')) ?? '';

            if (this.thousandSeparator === this.decimalMark) {
                this.thousandSeparator = '';
            }

            this.itemScope = this.getMetadata().get(['entityDefs', this.model.entityType, 'links', 'items', 'entity']);
            this.rows = [];
            this.source = undefined;
            this.preview = null;
            this.previewSeq = 0;
            this.costShown = null;
            // The table no longer matches this.rows (lines moved, added or removed) until the next render.
            this.domStale = false;

            this.listenTo(this.model, HEADER.map(attribute => `change:${attribute}`).join(' '), () => {
                if (this.isEditMode()) {
                    this.schedulePreview();
                }
            });

            this.addHandler('change', '[data-field]', (e, target) => this.onInput(target));
            this.addActionHandler('addLine', () => this.addLine());
            this.addActionHandler('removeLine', (e, target) => this.removeLine(Number(target.dataset.index)));
            this.addActionHandler('moveLine', (e, target) =>
                this.moveLine(Number(target.dataset.index), Number(target.dataset.step)));
            this.addActionHandler('selectProduct', (e, target) => this.selectProduct(Number(target.dataset.index)));
            this.addActionHandler('toggleCost', (e, target) => {
                this.syncInputs();
                this.costShown = target.checked;
                this.domStale = true;
                this.reRender();
            });
        }

        data() {
            const rows = this.currentRows();
            const isEdit = this.isEditMode();
            const text = (value, scale) => isEdit ?
                DecimalText.format(value, {decimalMark: this.decimalMark, grouping: false}) :
                DecimalText.format(value, {
                    decimalMark: this.decimalMark,
                    thousandSeparator: this.thousandSeparator,
                    minScale: scale,
                });
            const money = value => DecimalText.format(value, {
                decimalMark: this.decimalMark,
                thousandSeparator: this.thousandSeparator,
                minScale: 2,
            });

            const lines = rows.map((row, index) => {
                const invalid = row._invalid || {};
                const percent = this.discountIsPercent(row);
                const discount = percent ? row.discountPercent : row.discountAmount;
                const field = (name, scale) => name in invalid ? invalid[name] : text(row[name], scale);

                return {
                    index: index,
                    number: index + 1,
                    productId: row.productId,
                    productName: row.productName,
                    description: row.description,
                    quantity: field('quantity', 0),
                    unitPrice: field('unitPrice', 2),
                    discount: 'discount' in invalid ? invalid.discount : text(discount, percent ? 0 : 2),
                    discountIsPercent: percent,
                    discountText: DecimalText.isZero(discount) ? '' :
                        text(discount, percent ? 0 : 2) + (percent ? ' %' : ''),
                    taxRate: field('taxRate', 0),
                    hasTax: !DecimalText.isZero(row.taxRate),
                    purchaseCost: field('purchaseCost', 2),
                    amount: this.lineAmount(index, row, money),
                    invalid: invalid,
                    isFirst: index === 0,
                    isLast: index === rows.length - 1,
                };
            });

            return {
                ...super.data(),
                lines: lines,
                isEmpty: rows.length === 0,
                isEdit: isEdit,
                showCost: this.costShown ?? rows.some(row => !DecimalText.isZero(row.purchaseCost)),
                labels: this.labels(),
                sourceNote: !isEdit && this.model.get('sourceFormula') ?
                    this.translate('financeSourceTotals', 'labels') : null,
            };
        }

        afterRender() {
            super.afterRender();

            this.domStale = false;

            if (this.isEditMode()) {
                this.renderPreview();

                // A new document (a copy, «Создать заказ») shows its totals before the first edit.
                if (this.model.isNew() && this.rows.length && !this.preview) {
                    this.schedulePreview();
                }
            }
        }

        fetch() {
            // Ctrl+S saves without a change event: take the values still sitting in the focused cell first.
            this.syncInputs();

            const list = this.rows.map(row => {
                const line = {};

                for (const key of SENT) {
                    if (row[key] !== undefined) {
                        line[key] = row[key];
                    }
                }

                return line;
            });

            // The model gets this very array: currentRows() then knows it is ours, not an external change.
            this.source = list;

            return {[this.name]: list};
        }

        validate() {
            if (!this.isEditMode()) {
                return false;
            }

            if (this.rows.length === 0) {
                this.showValidationMessage(this.translate('financeNoLines', 'labels'));

                return true;
            }

            for (const [index, row] of this.rows.entries()) {
                const line = String(index + 1);

                if (row._invalid && Object.keys(row._invalid).length) {
                    this.showValidationMessage(this.translate('financeLineInvalid', 'labels').replace('{line}', line));

                    return true;
                }

                if (!row.productId) {
                    this.showValidationMessage(this.translate('financeLineProduct', 'labels').replace('{line}', line));

                    return true;
                }

                if (!row.quantity || row.unitPrice === '' || row.unitPrice === null || row.unitPrice === undefined) {
                    this.showValidationMessage(this.translate('financeLineRequired', 'labels').replace('{line}', line));

                    return true;
                }
            }

            return false;
        }

        /**
         * The rows of the model value; reset when the value changes from outside (load, save, another view).
         */
        currentRows() {
            const source = this.model.get(this.name);

            if (source !== this.source) {
                this.source = source;
                this.rows = (Array.isArray(source) ? source : []).map(row => ({...row}));
                this.preview = null;
            }

            return this.rows;
        }

        discountIsPercent(row) {
            return row._discountType ? row._discountType === 'percent' : !DecimalText.isZero(row.discountPercent);
        }

        onInput(target) {
            if (this.applyInput(target)) {
                this.changed();
            }
        }

        /**
         * Text and number cells of the table → rows (no events; a select is applied on its change only).
         */
        syncInputs() {
            if (!this.isEditMode() || !this.element || this.domStale) {
                return;
            }

            this.element.querySelectorAll('input[data-field], textarea[data-field]').forEach(input => {
                this.applyInput(input);
            });
        }

        /**
         * @return {boolean} the row was found and updated
         */
        applyInput(target) {
            const tr = target.closest('tr');
            const index = tr ? Number(tr.dataset.index) : NaN;
            const field = target.dataset.field;
            const row = this.rows[index];

            if (!row) {
                return false;
            }

            row._invalid = row._invalid || {};

            if (field === 'description') {
                row.description = target.value === '' ? null : target.value;
            } else if (field === 'discountType') {
                const active = this.discountIsPercent(row) ? 'discountPercent' : 'discountAmount';
                const value = row[active];

                row._discountType = target.value;
                row.discountAmount = '0';
                row.discountPercent = '0';
                row[target.value === 'percent' ? 'discountPercent' : 'discountAmount'] = value ?? '0';
            } else {
                const value = DecimalText.parse(target.value, this.decimalMark, this.thousandSeparator);
                const cell = target.closest('td');

                if (value === null) {
                    row._invalid[field] = target.value;
                    cell.classList.add('has-error');
                } else {
                    delete row._invalid[field];
                    cell.classList.remove('has-error');

                    const key = field !== 'discount' ? field :
                        (this.discountIsPercent(row) ? 'discountPercent' : 'discountAmount');

                    row[key] = value === '' && key !== 'quantity' && key !== 'unitPrice' ? '0' : value;
                }

                if (field === 'taxRate') {
                    cell.classList.toggle('has-warning', !DecimalText.isZero(row.taxRate));
                }
            }

            return true;
        }

        addLine() {
            this.syncInputs();
            this.rows.push({
                productId: null,
                productName: null,
                description: null,
                quantity: '1',
                unitPrice: '',
                discountAmount: '0',
                discountPercent: '0',
                taxRate: '0',
                purchaseCost: '0',
            });

            this.changed(true);
        }

        removeLine(index) {
            this.syncInputs();
            this.rows.splice(index, 1);
            this.changed(true);
        }

        moveLine(index, step) {
            const target = index + step;

            if (target < 0 || target >= this.rows.length) {
                return;
            }

            this.syncInputs();
            [this.rows[index], this.rows[target]] = [this.rows[target], this.rows[index]];
            this.changed(true);
        }

        async selectProduct(index) {
            Espo.Ui.notifyWait();

            const view = await this.createView('modal', 'views/modals/select-records', {
                entityType: 'Product',
                createButton: false,
                mandatorySelectAttributeList: ['name', 'unitPrice', 'description'],
                onSelect: models => {
                    const product = models[0];
                    const row = this.rows[index];

                    if (!product || !row) {
                        return;
                    }

                    this.syncInputs();
                    row.productId = product.id;
                    row.productName = product.get('name');

                    if (DecimalText.isZero(row.unitPrice) && product.get('unitPrice') !== null) {
                        row.unitPrice = DecimalText.parse(product.get('unitPrice') ?? '', '.', '') || row.unitPrice;
                    }

                    if (!row.description && product.get('description')) {
                        row.description = product.get('description');
                    }

                    this.changed(true);
                },
            });

            await view.render();
            Espo.Ui.notify();
        }

        /**
         * @param {boolean} [reRender] the table structure changed
         */
        changed(reRender = false) {
            this.preview = null;
            // The change event makes the form fetch() at once, before the new table is rendered.
            this.domStale = this.domStale || reRender;
            this.trigger('change');

            if (reRender) {
                this.reRender();
            }

            this.schedulePreview();
        }

        schedulePreview() {
            clearTimeout(this.previewTimer);
            this.preview = null;
            // Every change starts a new generation: a request already on its way is answered for older data.
            const seq = ++this.previewSeq;
            this.renderPreview(true);
            this.previewTimer = setTimeout(() => this.requestPreview(seq), PREVIEW_DELAY);
        }

        async requestPreview(seq) {
            if (
                seq !== this.previewSeq ||
                !this.isEditMode() ||
                this.rows.some(row => row._invalid && Object.keys(row._invalid).length)
            ) {
                return;
            }

            const attributes = {
                // The preview does not look products up: a line without one yet is still calculated.
                itemList: this.fetch()[this.name].map(line => ({...line, productId: line.productId || '-'})),
            };

            for (const attribute of HEADER) {
                attributes[attribute] = this.model.get(attribute) ?? null;
            }

            let result;

            try {
                result = await Espo.Ajax.postRequest(`FinanceDocument/${this.model.entityType}/calculate`, {
                    id: this.model.isNew() ? null : this.model.id,
                    attributes: attributes,
                });
            } catch (e) {
                return;
            }

            if (seq !== this.previewSeq || !this.isEditMode()) {
                return;
            }

            this.preview = result;
            this.renderPreview();
        }

        lineAmount(index, row, money) {
            const line = this.preview && this.preview.recalculated && this.preview.lines ?
                this.preview.lines[index] : null;

            if (line) {
                return money(line.amount);
            }

            // A new line has no amount until the server calculates it.
            return this.isEditMode() && !row.id ? '—' : money(row.amount);
        }

        /**
         * Amount cells and the totals line of the edit form, updated in place (inputs keep their focus).
         *
         * @param {boolean} [pending]
         */
        renderPreview(pending = false) {
            if (!this.element || !this.isEditMode()) {
                return;
            }

            const money = value => DecimalText.format(value, {
                decimalMark: this.decimalMark,
                thousandSeparator: this.thousandSeparator,
                minScale: 2,
            });

            this.element.querySelectorAll('[data-role="amount"]').forEach(cell => {
                const index = Number(cell.dataset.index);
                const row = this.rows[index];

                cell.textContent = pending ? '…' : (row ? this.lineAmount(index, row, money) : '');
            });

            const box = this.element.querySelector('[data-role="preview"]');

            if (!box) {
                return;
            }

            box.replaceChildren();
            box.classList.remove('text-danger', 'text-muted');

            if (pending || !this.preview) {
                box.classList.add('text-muted');
                box.textContent = pending ? this.translate('financeTotalsPending', 'labels') : '';

                return;
            }

            if (this.preview.error) {
                box.classList.add('text-danger');
                box.textContent = this.preview.error.message;

                return;
            }

            if (!this.preview.recalculated) {
                box.classList.add('text-muted');
                box.textContent = this.model.get('sourceFormula') ? this.translate('financeSourceTotals', 'labels') : '';

                return;
            }

            const scope = this.model.entityType;
            const parts = ['subtotal', 'discountAmount', 'shippingAmount', 'adjustment', 'grandTotal']
                .filter(name => name === 'subtotal' || name === 'grandTotal' || !DecimalText.isZero(this.preview[name]))
                .map(name => `${this.translate(name, 'fields', scope)}: ${money(this.preview[name])}`);

            const line = document.createElement('div');
            line.textContent = this.translate('financeTotalsPreview', 'labels') + ' ' + parts.join(' · ');
            box.appendChild(line);

            if (this.preview.replacesSourceTotals) {
                const note = document.createElement('div');
                note.className = 'text-warning';
                note.textContent = this.translate('financeReplacesSourceTotals', 'labels');
                box.appendChild(note);
            }
        }

        labels() {
            const field = name => this.translate(name, 'fields', this.itemScope);
            const label = name => this.translate(name, 'labels');

            return {
                order: field('order'),
                product: field('product'),
                description: field('description'),
                quantity: field('quantity'),
                unitPrice: field('unitPrice'),
                discount: this.translate('Discount', 'labels', this.itemScope),
                discountAmount: label('financeDiscountAmount'),
                discountPercent: label('financeDiscountPercent'),
                taxRate: field('taxRate'),
                purchaseCost: field('purchaseCost'),
                amount: field('amount'),
                addLine: label('financeAddLine'),
                removeLine: label('financeRemoveLine'),
                moveUp: label('financeMoveUp'),
                moveDown: label('financeMoveDown'),
                selectProduct: label('financeSelectProduct'),
            };
        }
    };
});
