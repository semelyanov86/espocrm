/**
 * Dashlet «Отчёт» (D-110): the chart or the table of a report, computed for the viewer by the same run as the report
 * page (POST Report/:id/run). The mode is the dashlet's option or the report's default; a tabular report or one without
 * charts shows the table (its first page and a link to the report). The main filter of the report (an enum field or
 * the owner) is a select in the dashlet header: «Все» or one of the values the report's conditions give; the choice is
 * kept in the dashlet options when the dashboard can be changed. A report the viewer cannot read shows «нет доступа».
 */
define('itvolga:views/dashlets/report', ['views/dashlets/abstract/base', 'itvolga:report/result-table'],
    (BaseView, ResultTable) => {

    const PAGE = 20;

    return class extends BaseView {

        name = 'Report'

        templateContent = `
            <div class="itv-report-dashlet">
                <div class="text-muted" data-role="message"></div>
                <div class="text-warning small" data-role="notes"></div>
                <div data-role="charts"></div>
                <div class="list" data-role="table"></div>
                <div class="small hidden" data-role="footer">
                    <span class="text-muted" data-role="counter"></span>
                    <a data-role="open"></a>
                </div>
            </div>`

        setup() {
            this.resultTable = new ResultTable(this);
            this.generation = 0;

            this.addActionHandler('drillDown', (e, target) => this.drillDown(JSON.parse(target.dataset.path)));
            this.on('resize', () => {
                const charts = this.getView('charts');

                charts && charts.trigger('resize');
            });
            this.once('remove', () => this.headingSelect() && this.headingSelect().remove());
        }

        afterRender() {
            this.load();
        }

        part(role) {
            return this.element.querySelector(`[data-role="${role}"]`);
        }

        showMessage(label) {
            this.clearView('charts');
            ['notes', 'charts', 'table'].forEach(role => this.part(role).innerHTML = '');
            this.part('footer').classList.add('hidden');
            this.part('message').textContent = this.translate(label, 'labels', 'Report');
        }

        async load() {
            const reportId = this.getOption('reportId');
            const generation = ++this.generation;

            if (!reportId) {
                this.showMessage('Select report');

                return;
            }

            let report;

            try {
                report = await Espo.Ajax.getRequest('Report/' + encodeURIComponent(reportId));
            } catch (xhr) {
                if (generation === this.generation && this.isRendered()) {
                    this.handleError(xhr);
                }

                return;
            }

            if (generation !== this.generation || !this.isRendered()) {
                return;
            }

            this.report = report;
            const dashboard = report.dashboard || {};
            const filterField = dashboard.filterField || null;
            const hasCharts = report.type !== 'tabular' && ((report.charts || {}).items || []).length > 0;
            this.mode = hasCharts ? (this.getOption('mode') || dashboard.mode || 'chart') : 'table';

            const stored = this.getOption('mainFilter');
            this.mainFilter = stored && stored.field === filterField ? stored : null;

            const body = {
                offset: 0,
                maxSize: PAGE,
                withQuickFilterOptions: false,
                withDashboardFilterOptions: !!filterField,
                quickFilters: this.mainFilter ? [{field: filterField, mode: 'in',
                    values: this.mainFilter.empty ? [] : [this.mainFilter.value],
                    includeEmpty: !!this.mainFilter.empty}] : [],
            };

            try {
                const result = await Espo.Ajax.postRequest(`Report/${encodeURIComponent(reportId)}/run`, body);

                if (generation !== this.generation || !this.isRendered()) {
                    return;
                }

                this.lastRun = body;
                this.result = result;
                this.renderResult(result, filterField);
            } catch (xhr) {
                if (generation === this.generation && this.isRendered()) {
                    this.handleError(xhr);
                }
            }
        }

        /** Nothing of an earlier result stays visible after a refusal. */
        handleError(xhr) {
            if (xhr && typeof xhr === 'object' && 'errorIsHandled' in xhr) {
                xhr.errorIsHandled = true;
            }

            const status = xhr && xhr.status;
            this.renderHeadingSelect(null, null);
            this.showMessage(status === 403 ? 'No access to report' : status === 404 ? 'Report not found' : 'No data');
        }

        async renderResult(result, filterField) {
            this.part('message').textContent = '';
            const notes = this.part('notes');
            notes.innerHTML = '';
            this.resultTable.limitNotes(result).forEach(text => notes.appendChild(this.resultTable.make('div', null,
                text)));

            this.renderHeadingSelect(filterField, result.dashboardFilter || null);
            this.clearView('charts');
            this.part('charts').innerHTML = '';
            this.part('table').innerHTML = '';

            const footer = this.part('footer');
            footer.classList.remove('hidden');
            this.part('counter').textContent = this.translate('Total records', 'labels', 'Report') + ': ' +
                result.recordCount;
            const open = this.part('open');
            open.textContent = this.translate('Open report', 'labels', 'Report');
            open.href = '#Report/view/' + encodeURIComponent(result.id);

            if (this.mode === 'chart' && result.charts) {
                const body = this.element.closest('.panel-body');
                const height = Math.max(160, (body ? body.clientHeight : 300) - 70);
                const view = await this.createView('charts', 'itvolga:views/report/charts', {
                    selector: '[data-role="charts"]',
                    chart: {...result.charts, title: ''},
                    height: height,
                });

                if (this.isRemoved()) {
                    view.remove();

                    return;
                }

                this.listenTo(view, 'drill-down', path => this.drillDown(path));
                await view.render();

                return;
            }

            const table = this.resultTable.build(result);

            if (table) {
                this.part('table').appendChild(table);
            }
        }

        headingSelect() {
            const container = this.getContainerView();
            const heading = container && container.element ? container.element.querySelector('.panel-heading') : null;

            return heading ? heading.querySelector('[data-role="itv-main-filter"]') : null;
        }

        /**
         * The main filter in the dashlet header: «Все», the values of the report's conditions, the empty value; options
         * go under opaque ids so any text stays a value.
         */
        renderHeadingSelect(filterField, options) {
            const old = this.headingSelect();

            if (old) {
                old.remove();
            }

            const container = this.getContainerView();
            const heading = container && container.element ? container.element.querySelector('.panel-heading') : null;

            if (!filterField || !options || !heading) {
                return;
            }

            const wrapper = document.createElement('div');
            wrapper.className = 'pull-right';
            wrapper.dataset.role = 'itv-main-filter';
            const select = document.createElement('select');
            select.className = 'form-control input-sm';
            select.title = options.label;
            const values = {};
            const add = (id, text, selected) => {
                const option = document.createElement('option');
                option.value = id;
                option.textContent = text;
                option.selected = selected;
                select.appendChild(option);
            };

            add('all', options.label + ': ' + this.translate('All values', 'labels', 'Report'), !this.mainFilter);
            options.options.forEach((option, i) => {
                const id = option.empty ? 'e' : 'v' + i;
                values[id] = option;
                add(id, option.f, !!this.mainFilter && (option.empty ? !!this.mainFilter.empty :
                    !this.mainFilter.empty && String(option.v) === String(this.mainFilter.value)));
            });

            // A choice the conditions no longer give stays chosen, so the shown data match the select.
            if (this.mainFilter && !select.querySelector('option:checked:not([value="all"])')) {
                add('kept', this.mainFilter.text || String(this.mainFilter.value), true);
                values.kept = {v: this.mainFilter.value, f: this.mainFilter.text, empty: this.mainFilter.empty};
            }

            // The heading is the drag handle of the dashboard grid.
            select.addEventListener('mousedown', e => e.stopPropagation());
            select.addEventListener('change', () => {
                const option = values[select.value];
                this.saveMainFilter(option ? {field: filterField, value: option.empty ? null : String(option.v),
                    empty: !!option.empty, text: option.f} : null);
            });

            wrapper.appendChild(select);
            heading.insertBefore(wrapper, heading.querySelector('.panel-title'));
        }

        saveMainFilter(filter) {
            this.optionsData.mainFilter = filter;

            if (!this.options.readOnly) {
                const all = Espo.Utils.cloneDeep(this.getPreferences().get('dashletsOptions') || {});
                all[this.id] = {...(all[this.id] || {}), mainFilter: filter};
                this.getPreferences().save({dashletsOptions: all}, {patch: true});
            }

            this.load();
        }

        drillDown(path) {
            if (!this.result) {
                return;
            }

            this.createView('drillDown', 'itvolga:views/report/modals/drill-down', {
                reportId: this.result.id,
                entityType: this.result.entityType,
                path: path,
                filters: null,
                quickFilters: (this.lastRun || {}).quickFilters || [],
            }, view => view.render());
        }

        actionRefresh() {
            this.load();
        }
    };
});
