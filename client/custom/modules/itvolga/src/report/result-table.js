/**
 * Tables of a report result (reports.md §6) as DOM elements, shared by the result page and the dashlet «Отчёт»: the
 * tabular rows with totals and calculations and the pager, summaries as nested group rows, summaries with details as
 * group headers with records, the matrix with row and column totals; the limit notes. Values come formatted by the
 * server (cell.f); links lead to the records. Clicks are left to the owning view: a group's button carries
 * data-action="drillDown" with its path, a pager button data-action="page" with its offset.
 */
define('itvolga:report/result-table', [], () => {

    return class {

        /**
         * @param {module:view} view the owning view (translations)
         */
        constructor(view) {
            this.view = view;
            this.result = null;
        }

        translate(label, category, scope) {
            return this.view.translate(label, category, scope);
        }

        getLanguage() {
            return this.view.getLanguage();
        }

        /**
         * The table of a result of any type (or a «No data» note).
         */
        build(result) {
            this.result = result;

            return result.type === 'tabular' ? this.tabular(result) :
                result.type === 'matrix' ? this.matrix(result) : this.grouped(result);
        }

        make(tag, className, text) {
            const element = document.createElement(tag);

            if (className) {
                element.className = className;
            }

            if (text !== undefined && text !== null) {
                element.textContent = text;
            }

            return element;
        }

        /** A value cell: a link to the record for link values and for the name of the main record. */
        cell(value, recordId, isName, numeric) {
            const td = this.make('td', numeric ? 'text-right' : null);

            if (!value) {
                return td;
            }

            if (value.id && value.et) {
                const a = this.make('a', null, value.f);
                a.href = `#${value.et}/view/${value.id}`;
                td.appendChild(a);
            } else if (isName && recordId) {
                const a = this.make('a', null, value.f);
                a.href = `#${this.result.entityType}/view/${recordId}`;
                td.appendChild(a);
            } else {
                td.textContent = value.f;
            }

            if (value.mixed) {
                td.classList.add('text-warning');
            }

            return td;
        }

        limitNotes(result) {
            const limits = result.limits || {};
            const t = (label, n) => this.translate(label, 'labels', 'Report').replace('{n}', n);
            const list = [];

            if (limits.rowLimitHit) {
                list.push(t('limitedRows', limits.rowLimit));
            }

            if (limits.groupLimitHit) {
                list.push(t('limitedGroups', limits.groupLimit));
            }

            if (limits.capHit) {
                list.push(t('limitedCap', limits.maxRows));
            }

            if (limits.matrixColumnsHit) {
                list.push(t('limitedColumns', limits.maxMatrixColumns));
            }

            return list;
        }

        headerRow(labels, numericFlags) {
            const tr = this.make('tr');

            labels.forEach((label, i) => tr.appendChild(this.make('th', numericFlags && numericFlags[i] ? 'text-right' : null,
                label)));

            return tr;
        }

        tabular(result) {
            if (!result.rows.length) {
                return this.make('div', 'text-muted', this.translate('No data', 'labels', 'Report'));
            }

            const table = this.make('table', 'table table-bordered table-condensed');
            const thead = this.make('thead');
            const labels = [...result.columns.map(c => c.label), ...result.calculations.map(c => c.label)];
            const numeric = [...result.columns.map(c => c.numeric), ...result.calculations.map(() => true)];
            thead.appendChild(this.headerRow(labels, numeric));
            table.appendChild(thead);
            const tbody = this.make('tbody');

            result.rows.forEach(row => {
                const tr = this.make('tr');
                row.cells.forEach((value, i) => tr.appendChild(this.cell(value, row.id, result.columns[i].field === 'name',
                    result.columns[i].numeric)));
                row.calc.forEach(value => tr.appendChild(this.cell(value, null, false, true)));
                tbody.appendChild(tr);
            });

            table.appendChild(tbody);
            const totals = this.tabularTotals(result);

            if (totals) {
                table.appendChild(totals);
            }

            return table;
        }

        tabularTotals(result) {
            const functions = ['SUM', 'AVG', 'MIN', 'MAX'].filter(fn =>
                Object.values(result.totals || {}).some(t => t[fn]) ||
                Object.values(result.calculationTotals || {}).some(t => t[fn]));

            if (!functions.length) {
                return null;
            }

            const tfoot = this.make('tfoot');
            const capped = result.limits && result.limits.calculationsCapped;

            functions.forEach(fn => {
                const tr = this.make('tr');
                result.columns.forEach((column, i) => {
                    const total = (result.totals[column.key] || {})[fn];

                    if (i === 0 && !total) {
                        tr.appendChild(this.make('th', null, this.getLanguage().translateOption(fn, 'aggregateFunction',
                            'Report')));

                        return;
                    }

                    tr.appendChild(this.cell(total, null, false, true));
                });
                result.calculations.forEach(c => {
                    const td = this.cell((result.calculationTotals[c.key] || {})[fn], null, false, true);

                    if (capped && (result.calculationTotals[c.key] || {})[fn]) {
                        td.title = this.translate('calculationsCapped', 'labels', 'Report')
                            .replace('{n}', result.limits.maxRows);
                        td.classList.add('text-warning');
                    }

                    tr.appendChild(td);
                });
                tfoot.appendChild(tr);
            });

            return tfoot;
        }

        pager(result) {
            const total = result.availableRows;

            if (total <= result.maxSize && result.offset === 0) {
                return null;
            }

            const box = this.make('div', 'btn-group');
            const prev = this.make('button', 'btn btn-default btn-sm', '«');
            prev.type = 'button';
            prev.dataset.action = 'page';
            prev.dataset.offset = String(Math.max(0, result.offset - result.maxSize));
            prev.disabled = result.offset === 0;
            const next = this.make('button', 'btn btn-default btn-sm', '»');
            next.type = 'button';
            next.dataset.action = 'page';
            next.dataset.offset = String(result.offset + result.maxSize);
            next.disabled = result.offset + result.maxSize >= total;
            const info = this.make('span', 'btn btn-default btn-sm disabled',
                `${result.offset + 1}–${Math.min(total, result.offset + result.maxSize)} / ${total}`);
            box.append(prev, info, next);

            return box;
        }

        drillButton(path) {
            const button = this.make('button', 'btn btn-link btn-sm btn-icon');
            button.type = 'button';
            button.dataset.action = 'drillDown';
            button.dataset.path = JSON.stringify(path);
            button.title = this.translate('Show records', 'labels', 'Report');
            button.appendChild(this.make('span', 'fas fa-list fa-sm'));

            return button;
        }

        grouped(result) {
            if (!result.tree.length) {
                return this.make('div', 'text-muted', this.translate('No data', 'labels', 'Report'));
            }

            const table = this.make('table', 'table table-bordered table-condensed');
            const thead = this.make('thead');
            const tbody = this.make('tbody');
            const levels = result.groups.length;
            const details = result.type === 'summariesWithDetails';
            const columns = details ? result.columns : [];
            const width = Math.max(levels + result.aggregates.length, columns.length);

            if (details) {
                thead.appendChild(this.headerRow(columns.map(c => c.label), columns.map(c => c.numeric)));
            } else {
                thead.appendChild(this.headerRow([...result.groups.map(g => g.label), ...result.aggregates.map(a => a.label)],
                    [...result.groups.map(() => false), ...result.aggregates.map(() => true)]));
            }

            const addNode = (node, level, path) => {
                const nodePath = [...path, node.key.v];

                if (details) {
                    const header = this.make('tr', 'active');
                    const th = this.make('th');
                    th.colSpan = columns.length;
                    th.appendChild(document.createTextNode(result.groups[0].label + ' = '));
                    th.appendChild(this.cell(node.key).firstChild || document.createTextNode(node.key.f));
                    th.appendChild(document.createTextNode(` (${node.count})` + (result.aggregates.length ? ': ' : '') +
                        result.aggregates.map((a, i) => a.label + ' ' + node.values[i].f).join('; ')));
                    th.appendChild(this.drillButton(nodePath));
                    header.appendChild(th);
                    tbody.appendChild(header);

                    (node.rows || []).forEach(row => {
                        const tr = this.make('tr');
                        row.cells.forEach((value, i) => tr.appendChild(this.cell(value, row.id, columns[i].field === 'name',
                            columns[i].numeric)));
                        tbody.appendChild(tr);
                    });

                    return;
                }

                const tr = this.make('tr', level === 0 && levels > 1 ? 'active' : null);

                for (let i = 0; i < levels; i++) {
                    if (i === level) {
                        const td = this.cell(node.key);
                        td.appendChild(this.drillButton(nodePath));
                        tr.appendChild(td);
                    } else {
                        tr.appendChild(this.make('td'));
                    }
                }

                node.values.forEach(value => tr.appendChild(this.cell(value, null, false, true)));
                tbody.appendChild(tr);
                (node.children || []).forEach(child => addNode(child, level + 1, nodePath));
            };

            result.tree.forEach(node => addNode(node, 0, []));
            table.append(thead, tbody);

            const tfoot = this.make('tfoot');
            const total = this.make('tr');
            const label = this.make('th', null, this.translate('Total', 'labels', 'Report') + ` (${result.grandTotal.count})`);

            if (details) {
                label.colSpan = width;
                label.textContent += result.aggregates.length ? ': ' + result.aggregates
                    .map((a, i) => a.label + ' ' + result.grandTotal.values[i].f).join('; ') : '';
                total.appendChild(label);
            } else {
                label.colSpan = levels;
                total.appendChild(label);
                result.grandTotal.values.forEach(value => total.appendChild(this.cell(value, null, false, true)));
            }

            tfoot.appendChild(total);
            table.appendChild(tfoot);

            return table;
        }

        matrix(result) {
            const matrix = result.matrix;

            if (!matrix.rows.length) {
                return this.make('div', 'text-muted', this.translate('No data', 'labels', 'Report'));
            }

            const aggregates = result.aggregates;
            const span = aggregates.length;
            const table = this.make('table', 'table table-bordered table-condensed');
            const thead = this.make('thead');
            const top = this.make('tr');
            const corner = this.make('th', null, result.groups[0].label + ' \\ ' + result.groups[1].label);
            corner.rowSpan = span > 1 ? 2 : 1;
            top.appendChild(corner);

            matrix.columns.forEach(column => {
                const th = this.make('th', 'text-center');
                th.colSpan = span;
                th.appendChild(this.cell(column.key).firstChild || document.createTextNode(column.key.f));
                top.appendChild(th);
            });

            const totalHead = this.make('th', 'text-center', this.translate('Total', 'labels', 'Report'));
            totalHead.colSpan = span;
            top.appendChild(totalHead);
            thead.appendChild(top);

            if (span > 1) {
                const second = this.make('tr');
                [...matrix.columns, null].forEach(() => aggregates.forEach(a => second.appendChild(this.make('th',
                    'text-right', a.label))));
                thead.appendChild(second);
            }

            const tbody = this.make('tbody');

            matrix.rows.forEach((row, r) => {
                const tr = this.make('tr');
                const head = this.cell(row.key);
                head.appendChild(this.drillButton([row.key.v]));
                tr.appendChild(head);

                matrix.columns.forEach((column, c) => {
                    const cell = matrix.cells[r][c];
                    aggregates.forEach((a, i) => tr.appendChild(this.cell(cell ? cell.values[i] : null, null, false, true)));
                });

                row.values.forEach(value => tr.appendChild(this.cell(value, null, false, true)));
                tbody.appendChild(tr);
            });

            const tfoot = this.make('tfoot');
            const total = this.make('tr');
            total.appendChild(this.make('th', null, this.translate('Total', 'labels', 'Report')));
            matrix.columns.forEach(column => column.values.forEach(value => total.appendChild(this.cell(value, null, false,
                true))));
            result.grandTotal.values.forEach(value => total.appendChild(this.cell(value, null, false, true)));
            tfoot.appendChild(total);
            table.append(thead, tbody, tfoot);

            return table;
        }

    };
});
