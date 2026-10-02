/**
 * Allocation table of a payment (stage 04.4, owner decisions 2026-10-02): which invoices and sales orders the payment
 * pays, edited in the payment form and saved with it by one request (`allocationList`). One row per document; the
 * payment moves to another document by choosing another document in its row; removing a row cancels the allocation.
 * Amounts stay decimal strings: the allocated sum and the rest come from the server (a saved payment, or a preview of
 * the same rule while the form is edited — POST FinanceDocument/Payment/calculate). The browser does no arithmetic
 * with money. Also the audit view of the field: Update notes show the table before and after.
 */
define('itvolga:views/finance/fields/allocation-list', ['views/fields/base', 'itvolga:finance/decimal-text'],
    (BaseFieldView, DecimalText) => {

    /** Document types of a row: entity type → link of the allocation to it. */
    const TARGETS = {Invoice: 'invoice', SalesOrder: 'salesOrder'};
    const PREVIEW_DELAY = 400;

    const tableHead = `
        <thead><tr style="white-space: nowrap;">
            <th style="width: 3em;">№</th>
            <th>{{labels.document}}</th>
            <th class="text-right" style="width: 14em;">{{labels.amount}}</th>
            {{#if isEdit}}<th style="width: 4em;"></th>{{/if}}
        </tr></thead>`;

    return class extends BaseFieldView {

        listTemplateContent = ''

        detailTemplateContent = `
            {{#if isEmpty}}<span class="none-value">{{labels.none}}</span>{{else}}
            <div class="itv-allocation-list" style="overflow-x: auto;">
            <table class="table table-bordered-inside" style="margin-bottom: 0;">${tableHead}
            <tbody>{{#each rows}}<tr>
                <td>{{number}}</td>
                <td>{{#if url}}<a href="{{url}}">{{label}}</a>{{else}}{{label}}{{/if}}
                    <span class="text-muted small">{{typeLabel}}</span></td>
                <td class="text-right">{{amount}}</td>
            </tr>{{/each}}</tbody></table></div>{{/if}}
            {{#if summary}}<div class="small text-muted" style="margin-top: 4px;">{{summary}}</div>{{/if}}`

        editTemplateContent = `
            {{#if isOutgoing}}<div class="text-warning small" style="margin-bottom: 6px;">{{labels.outgoing}}</div>{{/if}}
            {{#unless isEmpty}}
            <div class="itv-allocation-list" style="overflow-x: auto;">
            <table class="table table-bordered-inside" style="margin-bottom: 4px; min-width: 40em;">${tableHead}
            <tbody>{{#each rows}}<tr data-index="{{index}}">
                <td>{{number}}</td>
                <td><div class="input-group input-group-sm {{#if noDocument}}has-error{{/if}}">
                    <input type="text" class="form-control" value="{{typeLabel}}: {{label}}" title="{{label}}" readonly>
                    <span class="input-group-btn"><button type="button" class="btn btn-default btn-icon"
                        data-action="selectDocument" data-index="{{index}}" title="{{../labels.select}}">
                        <span class="fas fa-angle-up"></span></button></span></div></td>
                <td class="{{#if invalid}}has-error{{/if}}"><input type="text" inputmode="decimal"
                    class="form-control input-sm text-right" data-field="amount" value="{{amountInput}}"></td>
                <td class="text-nowrap"><button type="button" class="btn btn-link btn-sm btn-icon"
                    data-action="removeAllocation" data-index="{{index}}" title="{{../labels.remove}}">
                    <span class="fas fa-times"></span></button></td>
            </tr>{{/each}}</tbody></table></div>
            {{/unless}}
            {{#unless isOutgoing}}
            <button type="button" class="btn btn-default btn-sm" data-action="addAllocation" data-type="Invoice">
                <span class="fas fa-plus fa-sm"></span> {{labels.addInvoice}}</button>
            <button type="button" class="btn btn-default btn-sm" data-action="addAllocation" data-type="SalesOrder">
                <span class="fas fa-plus fa-sm"></span> {{labels.addSalesOrder}}</button>
            {{/unless}}
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

            this.isAudit = !!this.options.auditData;
            this.rows = [];
            this.source = undefined;
            this.preview = null;
            this.previewSeq = 0;
            // The table no longer matches this.rows (rows added or removed) until the next render.
            this.domStale = false;

            this.listenTo(this.model, 'change:amount', () => {
                if (!this.isEditMode()) {
                    return;
                }

                if (this.followPaymentAmount(this.model.previous('amount'), this.model.get('amount'))) {
                    this.changed(true);

                    return;
                }

                this.schedulePreview();
            });

            this.listenTo(this.model, 'change:direction', () => {
                if (this.isEditMode()) {
                    this.syncInputs();
                    this.domStale = true;
                    this.reRender();
                    this.schedulePreview();
                }
            });

            this.addHandler('change', 'input[data-field]', (e, target) => this.onInput(target));
            // A cell typed back to its value on focus fires no change event, though Ctrl+S (syncInputs) may have
            // taken the intermediate value meanwhile.
            this.addHandler('focusout', 'input[data-field]', (e, target) => this.onInput(target, true));
            this.addActionHandler('addAllocation', (e, target) => this.selectDocument(null, target.dataset.type));
            this.addActionHandler('selectDocument', (e, target) => {
                const index = Number(target.dataset.index);

                this.selectDocument(index, this.typeOf(this.rows[index]));
            });
            this.addActionHandler('removeAllocation', (e, target) => this.removeRow(Number(target.dataset.index)));
        }

        data() {
            const rows = this.currentRows();
            const isEdit = this.isEditMode();
            const money = value => DecimalText.format(value, {
                decimalMark: this.decimalMark,
                thousandSeparator: this.thousandSeparator,
                minScale: 2,
            });

            return {
                ...super.data(),
                isEdit: isEdit,
                isEmpty: rows.length === 0,
                isOutgoing: this.model.get('direction') === 'outgoing',
                labels: this.labels(),
                summary: !isEdit && !this.isAudit && rows.length ? this.summary(money) : null,
                rows: rows.map((row, index) => {
                    const type = this.typeOf(row);
                    const link = TARGETS[type];
                    const id = link ? row[link + 'Id'] : null;

                    return {
                        index: index,
                        number: index + 1,
                        typeLabel: type ? this.translate(type, 'scopeNames') : '',
                        label: this.documentLabel(row, link),
                        url: id && !this.isAudit ? `#${type}/view/${id}` : null,
                        noDocument: !id,
                        amount: money(row.amount),
                        amountInput: '_invalid' in row ? row._invalid :
                            DecimalText.format(row.amount, {decimalMark: this.decimalMark, grouping: false}),
                        invalid: '_invalid' in row,
                    };
                }),
            };
        }

        afterRender() {
            super.afterRender();

            this.domStale = false;

            if (this.isEditMode()) {
                this.renderPreview();

                // The form shows its rest before the first edit (a prefilled «Добавить платёж», a reopened edit).
                if (this.rows.length && !this.preview) {
                    this.schedulePreview();
                }
            }
        }

        fetch() {
            // Ctrl+S saves without a change event: take the value still sitting in the focused cell first, and the
            // payment amount still sitting in its own field (the form sets the model silently on save).
            this.syncInputs();
            this.followPendingAmount();

            const list = this.rows.map(row => {
                const item = {};

                for (const key of ['id', 'invoiceId', 'invoiceName', 'salesOrderId', 'salesOrderName',
                    'documentNumber', 'amount']) {
                    if (row[key] !== undefined && row[key] !== null) {
                        item[key] = row[key];
                    }
                }

                return item;
            });

            // The model gets this very array: currentRows() then knows it is ours, not an external change.
            this.source = list;

            return {[this.name]: list};
        }

        validate() {
            if (!this.isEditMode()) {
                return false;
            }

            if (this.model.get('direction') === 'outgoing' && this.rows.length) {
                this.showValidationMessage(this.translate('financeOutgoingNoAllocations', 'labels'));

                return true;
            }

            const seen = {};

            for (const [index, row] of this.rows.entries()) {
                const line = String(index + 1);
                const link = TARGETS[this.typeOf(row)];
                const key = link ? link + ':' + row[link + 'Id'] : null;

                if ('_invalid' in row) {
                    this.showValidationMessage(
                        this.translate('financeAllocationInvalid', 'labels').replace('{line}', line));

                    return true;
                }

                if (!key || !row[link + 'Id'] || !row.amount) {
                    this.showValidationMessage(
                        this.translate('financeAllocationRequired', 'labels').replace('{line}', line));

                    return true;
                }

                if (seen[key]) {
                    this.showValidationMessage(
                        this.translate('financeAllocationDuplicate', 'labels').replace('{line}', line));

                    return true;
                }

                seen[key] = true;
            }

            return false;
        }

        /**
         * The rows of the model value; reset when the value changes from outside (load, save, cancel, another view).
         * A preview on its way was asked for the replaced table: its generation is dropped.
         */
        currentRows() {
            const source = this.model.get(this.name);

            if (source !== this.source) {
                this.source = source;
                this.rows = (Array.isArray(source) ? source : []).map(row => ({...row}));
                this.preview = null;
                this.previewSeq++;
                clearTimeout(this.previewTimer);
            }

            return this.rows;
        }

        /**
         * A payment of one document (the Vtiger shape, «Добавить платёж»): its only row follows the payment amount
         * while they are equal — a copy of the string, no arithmetic.
         *
         * @return {boolean} the row was changed
         */
        followPaymentAmount(previous, current) {
            const was = DecimalText.parse(String(previous ?? ''), '.', '');
            const now = DecimalText.parse(String(current ?? ''), '.', '');
            const row = this.rows.length === 1 ? this.rows[0] : null;

            if (!row || '_invalid' in row || !was || now === null || now === was ||
                DecimalText.canonical(String(row.amount)) !== was) {
                return false;
            }

            row.amount = now;

            return true;
        }

        /**
         * The amount typed into the payment field but not yet in the model (Ctrl+S right from that field).
         */
        followPendingAmount() {
            let view = this.getParentView();

            while (view && typeof view.getFieldView !== 'function') {
                view = view.getParentView();
            }

            const amountView = view ? view.getFieldView('amount') : null;

            if (!amountView || !amountView.isEditMode() || !amountView.isFullyRendered()) {
                return;
            }

            const pending = (amountView.fetch() || {}).amount;

            if (!this.followPaymentAmount(this.model.get('amount'), pending)) {
                return;
            }

            // A preview asked for the old amount must not be shown for the new one (the save may still be refused).
            this.schedulePreview();

            // The cell shows the new amount at once (no re-render inside the form's fetch, inputs keep working).
            const input = this.element && !this.domStale ?
                this.element.querySelector('tr[data-index="0"] input[data-field="amount"]') : null;

            if (input) {
                input.value = DecimalText.format(this.rows[0].amount, {decimalMark: this.decimalMark, grouping: false});
            }
        }

        typeOf(row) {
            for (const [type, link] of Object.entries(TARGETS)) {
                if (row && (row[link + 'Id'] || row._type === type)) {
                    return type;
                }
            }

            return null;
        }

        documentLabel(row, link) {
            const name = link ? row[link + 'Name'] : null;

            return [row.documentNumber, name].filter(Boolean).join(' · ');
        }

        summary(money) {
            const allocated = this.model.get('allocatedAmount');
            const rest = this.model.get('unallocatedAmount');

            if (allocated === null || allocated === undefined) {
                return null;
            }

            return `${this.translate('financeAllocated', 'labels')}: ${money(allocated)} · ` +
                `${this.translate('financeUnallocated', 'labels')}: ${money(rest)}`;
        }

        /**
         * @param {Element} target
         * @param {boolean} [onLeave] only when the value differs from the row
         */
        onInput(target, onLeave = false) {
            const before = onLeave ? JSON.stringify(this.rows) : null;

            if (this.applyInput(target) && (!onLeave || JSON.stringify(this.rows) !== before)) {
                this.changed();
            }
        }

        /**
         * The amount cells → rows (no events).
         */
        syncInputs() {
            if (!this.isEditMode() || !this.element || this.domStale) {
                return;
            }

            const before = JSON.stringify(this.rows);

            this.element.querySelectorAll('input[data-field]').forEach(input => this.applyInput(input));

            if (JSON.stringify(this.rows) !== before) {
                this.schedulePreview();
            }
        }

        /**
         * @return {boolean} the row was found and updated
         */
        applyInput(target) {
            const tr = target.closest('tr');
            const row = tr && !this.domStale ? this.rows[Number(tr.dataset.index)] : null;

            if (!row) {
                return false;
            }

            const value = DecimalText.parse(target.value, this.decimalMark, this.thousandSeparator);
            const cell = target.closest('td');

            if (value === null) {
                row._invalid = target.value;
                cell.classList.add('has-error');
            } else {
                delete row._invalid;
                cell.classList.remove('has-error');
                row.amount = value;
            }

            return true;
        }

        removeRow(index) {
            this.syncInputs();
            this.rows.splice(index, 1);
            this.changed(true);
        }

        /**
         * A document for a new row (index null) or another document for a row (the payment moves to it, the row
         * and its id stay).
         *
         * @param {number|null} index
         * @param {string} type
         */
        async selectDocument(index, type) {
            if (!TARGETS[type]) {
                return;
            }

            Espo.Ui.notifyWait();

            const view = await this.createView('modal', 'views/modals/select-records', {
                entityType: type,
                createButton: false,
                mandatorySelectAttributeList: ['name', 'number'],
                filters: this.payerFilters(),
                onSelect: models => {
                    const document = models[0];

                    if (!document) {
                        return;
                    }

                    this.syncInputs();

                    let row = index === null ? null : this.rows[index];

                    if (!row) {
                        row = {amount: this.rows.length ? '' : this.paymentAmount()};
                        this.rows.push(row);
                    }

                    for (const link of Object.values(TARGETS)) {
                        row[link + 'Id'] = null;
                        row[link + 'Name'] = null;
                    }

                    row._type = type;
                    row[TARGETS[type] + 'Id'] = document.id;
                    row[TARGETS[type] + 'Name'] = document.get('name');
                    row.documentNumber = document.get('number');

                    this.changed(true);
                },
            });

            await view.render();
            Espo.Ui.notify();
        }

        /**
         * Documents of the payer's account first (the filter can be removed in the dialog).
         */
        payerFilters() {
            if (this.model.get('payerType') !== 'Account' || !this.model.get('payerId')) {
                return undefined;
            }

            return {
                account: {
                    type: 'equals',
                    attribute: 'accountId',
                    value: this.model.get('payerId'),
                    data: {type: 'is', nameValue: this.model.get('payerName')},
                },
            };
        }

        /**
         * The payment amount as text for the first row (a copy of the string, no arithmetic).
         */
        paymentAmount() {
            const amount = this.model.get('amount');

            return amount === null || amount === undefined ? '' : DecimalText.parse(String(amount), '.', '') ?? '';
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
            if (seq !== this.previewSeq || !this.isEditMode()) {
                return;
            }

            const list = this.fetch()[this.name];

            if (seq !== this.previewSeq || this.rows.some(row => '_invalid' in row || !this.typeOf(row))) {
                return;
            }

            let result;

            try {
                result = await Espo.Ajax.postRequest(`FinanceDocument/${this.model.entityType}/calculate`, {
                    id: this.model.isNew() ? null : this.model.id,
                    attributes: {
                        amount: this.model.get('amount') ?? null,
                        direction: this.model.get('direction') ?? null,
                        [this.name]: list,
                    },
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

        /**
         * @param {boolean} [pending]
         */
        renderPreview(pending = false) {
            const box = this.element && this.isEditMode() ? this.element.querySelector('[data-role="preview"]') : null;

            if (!box) {
                return;
            }

            box.classList.remove('text-danger', 'text-muted');

            if (pending || !this.preview) {
                box.classList.add('text-muted');
                box.textContent = pending ? this.translate('financeAllocationsPending', 'labels') : '';

                return;
            }

            if (this.preview.error) {
                box.classList.add('text-danger');
                box.textContent = this.preview.error.message;

                return;
            }

            const money = value => DecimalText.format(value, {
                decimalMark: this.decimalMark,
                thousandSeparator: this.thousandSeparator,
                minScale: 2,
            });

            box.textContent = `${this.translate('financeAllocated', 'labels')}: ` +
                `${money(this.preview.allocatedAmount)} · ${this.translate('financeUnallocated', 'labels')}: ` +
                money(this.preview.unallocatedAmount);
        }

        labels() {
            const label = name => this.translate(name, 'labels');

            return {
                document: label('financeAllocationDocument'),
                amount: label('financeAllocationAmount'),
                none: label('financeNoAllocations'),
                outgoing: label('financeOutgoingNoAllocations'),
                addInvoice: label('financeAddInvoice'),
                addSalesOrder: label('financeAddSalesOrder'),
                select: label('financeSelectDocument'),
                remove: label('financeRemoveAllocation'),
            };
        }
    };
});
