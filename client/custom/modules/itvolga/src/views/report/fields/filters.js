/**
 * Conditions of a report (reports.md §4): groups of conditions joined by AND/OR, inside a group and between groups.
 * A condition is a field of the main entity or of an entity one link away, edited by the core search view of the
 * field (views/search/filter on a model of the field's entity); the report keeps both the UI state of the view
 * (`advanced`) and the core where item made of it (`where`, attributes of the field's entity). Periods are stored as
 * their type; the server resolves them at every run. «Compare dates» compares two date fields of the main entity.
 *
 * The same view edits the one-off conditions on the result page (option `runtime`).
 */
define('itvolga:views/report/fields/filters', ['itvolga:views/report/fields/base'], (BaseView) => {

    const MAX_DEPTH = 2;
    const COMPARE = '__compare';
    const OPERATORS = ['lessThan', 'lessThanOrEquals', 'equals', 'notEquals', 'greaterThanOrEquals', 'greaterThan'];

    return class extends BaseView {

        emptyValue() {
            return {type: 'and', items: []};
        }

        detailTemplateContent = `{{#if text}}<div class="itv-report-conditions">{{{text}}}</div>{{else}}<span
            class="none-value">{{translate 'None'}}</span>{{/if}}`

        editTemplateContent = `<div class="itv-report-filters" data-role="root"></div>`

        setup() {
            super.setup();
            this.counter = 0;
            this.nodes = {};

            this.addActionHandler('addCondition', (e, target) => this.addCondition(target.dataset.group));
            this.addActionHandler('addGroup', () => this.addGroup());
            this.addActionHandler('removeNode', (e, target) => this.removeNode(target.dataset.node));
            this.addHandler('change', 'select[data-role="operator"]', (e, target) => {
                this.syncViews();
                this.findGroup(target.dataset.group).type = target.value;
                this.commit(false);
            });
            this.addHandler('change', 'select[data-compare]', (e, target) => {
                const node = this.nodes[target.dataset.node];
                const value = node.where.value || {};

                if (target.dataset.compare === 'left') {
                    node.field = target.value;
                    node.where.attribute = target.value;
                } else {
                    value[target.dataset.compare] = target.value;
                }

                node.where.value = value;
                this.commit(false);
            });
        }

        /** Every node gets a runtime id (not stored). */
        index(group, path = 'g') {
            group.$id = path;
            this.nodes[path] = group;

            (group.items || []).forEach((item, i) => {
                const id = path + '-' + i;

                if (item.items) {
                    this.index(item, id);
                } else {
                    item.$id = id;
                    this.nodes[id] = item;
                }
            });
        }

        findGroup(id) {
            return this.nodes[id] && this.nodes[id].items ? this.nodes[id] : this.state;
        }

        isGroup(node) {
            return Array.isArray(node.items);
        }

        afterRender() {
            super.afterRender();

            if (!this.isEditMode()) {
                return;
            }

            this.nodes = {};
            this.index(this.state);

            const root = this.element.querySelector('[data-role="root"]');
            root.innerHTML = '';
            root.appendChild(this.renderGroup(this.state, 0));
            this.initSearchSelects();

            Object.values(this.nodes).forEach(node => {
                if (!this.isGroup(node)) {
                    this.createConditionView(node);
                }
            });
        }

        element_(tag, className, text) {
            const element = document.createElement(tag);

            if (className) {
                element.className = className;
            }

            if (text !== undefined) {
                element.textContent = text;
            }

            return element;
        }

        button(action, label, icon, data = {}) {
            const button = this.element_('button', icon ? 'btn btn-link btn-sm btn-icon' : 'btn btn-default btn-sm');
            button.type = 'button';
            button.dataset.action = action;
            Object.entries(data).forEach(([key, value]) => button.dataset[key] = value);

            if (icon) {
                button.title = label;
                button.appendChild(this.element_('span', icon));
            } else {
                button.textContent = label;
            }

            return button;
        }

        renderGroup(group, depth) {
            const panel = this.element_('div', depth === 0 ? '' : 'panel panel-default');
            const body = this.element_('div', depth === 0 ? '' : 'panel-body');
            const head = this.element_('div', 'form-inline');
            const operator = this.element_('select', 'form-control input-sm');
            operator.dataset.role = 'operator';
            operator.dataset.group = group.$id;

            ['and', 'or'].forEach(type => {
                const option = this.element_('option', null, this.translateReport(type === 'and' ? 'AND' : 'OR'));
                option.value = type;
                option.selected = group.type === type;
                operator.appendChild(option);
            });

            head.appendChild(operator);

            if (depth > 0) {
                head.appendChild(this.button('removeNode', this.translateReport('Remove'), 'fas fa-times',
                    {node: group.$id}));
            }

            body.appendChild(head);

            group.items.forEach(item => {
                body.appendChild(this.isGroup(item) ? this.renderGroup(item, depth + 1) : this.renderCondition(item));
            });

            const footer = this.element_('div', 'form-inline');
            const picker = this.element_('select', 'form-control input-sm itv-search');
            picker.dataset.role = 'picker';
            picker.dataset.group = group.$id;
            const empty = this.element_('option', null, '');
            empty.value = '';
            picker.appendChild(empty);

            this.fieldOptions(field => field.filter).forEach(option => {
                const element = this.element_('option', null, option.label);
                element.value = option.value;
                picker.appendChild(element);
            });

            if (this.dateFields().length > 1) {
                const compare = this.element_('option', null, '⇄ ' + this.translateReport('Compare dates'));
                compare.value = COMPARE;
                picker.appendChild(compare);
            }

            footer.appendChild(picker);
            footer.appendChild(this.button('addCondition', this.translateReport('Add Field Condition'), null,
                {group: group.$id}));

            if (depth + 1 < MAX_DEPTH) {
                footer.appendChild(this.button('addGroup', this.translateReport('Add Group')));
            }

            body.appendChild(footer);
            panel.appendChild(body);

            return panel;
        }

        dateFields() {
            return this.catalog.fields.filter(field => field.date);
        }

        renderCondition(node) {
            const box = this.element_('div', 'well well-sm');
            const head = this.element_('div');
            const type = (node.where || {}).type;
            head.appendChild(this.element_('strong', null, type === 'compareField' ?
                this.translateReport('Compare dates') : this.label(node.field)));
            head.appendChild(this.button('removeNode', this.translateReport('Remove'), 'fas fa-times', {node: node.$id}));
            box.appendChild(head);

            if (type === 'compareField') {
                box.appendChild(this.renderCompare(node));

                return box;
            }

            const container = this.element_('div', 'field');
            container.dataset.condition = node.$id;
            box.appendChild(container);

            return box;
        }

        renderCompare(node) {
            const row = this.element_('div', 'form-inline');
            const select = (key, options, value) => {
                const element = this.element_('select', 'form-control input-sm');
                element.dataset.compare = key;
                element.dataset.node = node.$id;

                options.forEach(option => {
                    const item = this.element_('option', null, option.label);
                    item.value = option.value;
                    item.selected = option.value === value;
                    element.appendChild(item);
                });

                return element;
            };
            const fields = this.dateFields().map(field => ({value: field.ref, label: field.label}));
            const value = node.where.value || {};

            row.appendChild(select('left', fields, node.where.attribute));
            row.appendChild(select('operator', OPERATORS.map(op => ({value: op,
                label: this.getLanguage().translateOption(op, 'havingOperator', 'Report') || op})), value.operator));
            row.appendChild(select('field', fields, value.field));

            return row;
        }

        viewNameFor(field) {
            if (field.family === 'date') {
                return 'itvolga:views/report/filter/date';
            }

            if (field.family === 'datetime') {
                return 'itvolga:views/report/filter/datetime';
            }

            if (field.family === 'link' && field.foreignEntityType === 'User') {
                return 'itvolga:views/report/filter/user';
            }

            return null;
        }

        createConditionView(node) {
            const field = this.catalog.byRef[node.field];

            if (!field || (node.where || {}).type === 'compareField') {
                return;
            }

            const key = 'condition-' + node.$id;

            this.getModelFactory().create(field.entityType).then(model => {
                if (!this.isRendered()) {
                    return;
                }

                this.createView(key, 'views/search/filter', {
                    selector: `[data-condition="${node.$id}"]`,
                    model: model,
                    name: field.field,
                    params: node.advanced || (node.where ? this.advancedFromWhere(node.where, field) : undefined),
                    viewName: this.viewNameFor(field) || undefined,
                }, view => {
                    view.render();
                    this.listenTo(view, 'change', () => {
                        node.touched = true;
                        this.syncViews();
                        this.trigger('change');
                    });
                });
            });
        }

        /**
         * UI state of a stored condition without one (a seeded condition): the search state the core field views read
         * for the common shapes; anything else starts empty in the view and stays stored until the user changes it.
         */
        advancedFromWhere(where, field) {
            const type = where.type;
            const value = where.value;
            const result = {type: type, value: value, data: {type: type}};
            const isEnum = field && field.family === 'enum';
            const isLink = field && field.family === 'link';

            if (isEnum && (type === 'equals' || type === 'notEquals')) {
                // The enum search view knows lists only: one value is a list of one.
                result.data = {type: type === 'equals' ? 'anyOf' : 'noneOf', valueList: [value]};
            } else if (isLink && (type === 'in' || type === 'notIn')) {
                // The link search view has its own operators; names are not stored, ids stand in for them.
                const ids = Array.isArray(value) ? value : [];
                result.data = {type: type === 'in' ? 'isOneOf' : 'isNotOneOf', oneOfIdList: ids,
                    oneOfNameHash: Object.fromEntries(ids.map(id => [id, id]))};
            } else if (isLink && type === 'notEquals') {
                result.data = {type: 'isNot', idValue: value, nameValue: value};
            } else if (type === 'in' || type === 'notIn') {
                result.data = {type: type === 'in' ? 'anyOf' : 'noneOf', valueList: value,
                    oneOfIdList: value, oneOfNameHash: {}};
            } else if (type === 'equals' && /Id$/.test(where.attribute || '')) {
                result.data = {type: 'is', idValue: value, nameValue: value};
            } else if (['on', 'after', 'before'].includes(type)) {
                result.data = {type: type, value: value};
            } else if (type === 'between' && Array.isArray(value)) {
                result.data = {type: type, value: value[0], valueTo: value[1], value1: value[0], value2: value[1]};
            } else if (['lastXDays', 'nextXDays', 'olderThanXDays', 'afterXDays', 'xDaysAgo', 'inXDays'].includes(type)) {
                result.data = {type: type, number: value};
            } else if (type === 'isNull') {
                result.data = {type: 'isEmpty'};
            } else if (type === 'isNotNull') {
                result.data = {type: 'isNotEmpty'};
            }

            return result;
        }

        /**
         * Reads the search views into the conditions: `advanced` as the view gives it, `where` the core item.
         */
        syncViews() {
            Object.values(this.nodes).forEach(node => {
                if (this.isGroup(node) || (node.where || {}).type === 'compareField') {
                    return;
                }

                // A stored condition the user did not touch keeps its where item: the search view may not represent
                // every stored value (e.g. a seeded condition without UI state).
                if (node.where && !node.touched) {
                    return;
                }

                const view = this.getView('condition-' + node.$id);
                const fieldView = view && view.getFieldView && view.getFieldView();

                if (!fieldView || !fieldView.isRendered()) {
                    return;
                }

                const advanced = fieldView.fetchSearch();
                const field = this.catalog.byRef[node.field];

                if (!advanced || !field) {
                    node.where = null;

                    return;
                }

                node.advanced = advanced;
                node.where = this.toWhere(advanced, field.field, field);
            });
        }

        /**
         * search-manager.getWherePart without the time zone (the server sets the runner's one).
         */
        toWhere(defs, name, field) {
            if (defs.type === 'or' || defs.type === 'and') {
                return {type: defs.type, value: (defs.value || []).map(item => this.toWhere(item, name, field))};
            }

            const where = {type: defs.type, attribute: defs.attribute || defs.field || name};

            if ('value' in defs && defs.value !== undefined) {
                where.value = field.family === 'number' ? this.decimalText(defs.value) : defs.value;
            }

            if (field.family === 'datetime') {
                where.dateTime = true;
            } else if (field.family === 'date') {
                where.date = true;
            }

            return where;
        }

        /**
         * Numbers of the core float search arrive as JSON numbers; the server takes decimal strings (D-93).
         */
        decimalText(value) {
            if (Array.isArray(value)) {
                return value.map(item => this.decimalText(item));
            }

            return typeof value === 'number' && !Number.isInteger(value) ? String(value) : value;
        }

        addCondition(groupId) {
            this.syncViews();
            const picker = this.element.querySelector(`select[data-role="picker"][data-group="${groupId}"]`);
            const ref = picker ? picker.value : '';
            const group = this.findGroup(groupId);

            if (!ref) {
                return;
            }

            if (ref === COMPARE) {
                const dates = this.dateFields();
                group.items.push({field: dates[0].ref, where: {type: 'compareField', attribute: dates[0].ref,
                    value: {operator: 'lessThan', field: dates[1].ref}}});
            } else {
                group.items.push({field: ref, where: null});
            }

            this.commit();
        }

        addGroup() {
            this.syncViews();
            this.state.items.push({type: 'and', items: []});
            this.commit();
        }

        removeNode(id) {
            this.syncViews();
            const remove = group => {
                group.items = group.items.filter(item => item.$id !== id);
                group.items.filter(item => this.isGroup(item)).forEach(remove);
            };

            remove(this.state);
            this.commit();
        }

        /**
         * The stored tree: runtime ids dropped, conditions without a value (an empty search view) left out.
         */
        clean(group) {
            return {
                type: group.type,
                items: group.items
                    .map(item => {
                        if (this.isGroup(item)) {
                            return this.clean(item);
                        }

                        if (!item.where || !item.where.attribute && !['and', 'or'].includes(item.where.type) ||
                            item.where.attribute === 'id') {
                            return null;
                        }

                        // Copies: the editor changes its condition objects in place (date comparison).
                        const result = {field: item.field, where: JSON.parse(JSON.stringify(item.where))};

                        if (item.advanced) {
                            result.advanced = JSON.parse(JSON.stringify(item.advanced));
                        }

                        return result;
                    })
                    .filter(item => item && (!item.items || item.items.length)),
            };
        }

        fetch() {
            if (this.isEditMode() && this.isRendered()) {
                this.syncViews();
            }

            return {[this.name]: this.clean(this.state)};
        }

        /** Readable text of the conditions (detail mode and the report info block). */
        describe(group, depth = 0) {
            const joiner = ' ' + this.translateReport(group.type === 'or' ? 'OR' : 'AND') + ' ';
            const parts = (group.items || []).map(item => {
                if (this.isGroup(item)) {
                    const inner = this.describe(item, depth + 1);

                    return inner ? '(' + inner + ')' : '';
                }

                return this.describeCondition(item);
            }).filter(Boolean);

            return parts.join(joiner);
        }

        describeCondition(item) {
            const escape = value => this.getHelper().escapeString(String(value ?? ''));
            const where = item.where || {};
            const lang = this.getLanguage();

            if (where.type === 'compareField') {
                return escape(this.label(where.attribute)) + ' ' +
                    escape(lang.translateOption(where.value.operator, 'havingOperator', 'Report')) + ' ' +
                    escape(this.label(where.value.field));
            }

            const advanced = item.advanced || {};
            const uiType = (advanced.data && advanced.data.type) || advanced.type || where.type;
            // Operator names of the core search views: dates, text, numbers, then the common ones.
            const typeLabel = ['dateSearchRanges', 'varcharSearchRanges', 'intSearchRanges', 'searchRanges']
                .map(list => lang.translateOption(uiType, list))
                .find(label => label !== uiType) || this.translate(uiType, 'searchRanges');
            const data = advanced.data || {};
            let values = [];

            if (data.valueList) {
                const field = this.catalog.byRef[item.field] || {};
                values = data.valueList.map(v => lang.translateOption(v, field.field, field.entityType));
            } else if (data.oneOfNameHash) {
                values = Object.values(data.oneOfNameHash);
            } else if (data.nameValue) {
                values = [data.nameValue];
            } else if (where.value !== undefined && where.value !== null && typeof where.value !== 'object') {
                values = [where.value];
            } else if (Array.isArray(where.value)) {
                values = where.value;
            }

            return '<strong>' + escape(this.label(item.field)) + '</strong>: ' + escape(typeLabel) +
                (values.length ? ' ' + escape(values.join(', ')) : '');
        }

        data() {
            return {
                ...super.data(),
                text: this.describe(this.state),
            };
        }
    };
});
