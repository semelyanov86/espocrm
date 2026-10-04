/**
 * Report builder: the core record form whose tabs are the steps (basics, grouping and aggregates, columns and sorting,
 * calculations, filters, labels, charts, access, dashboard); steps not used by the report type are hidden by logicDefs. «Сохранить»
 * keeps the builder open, «Сохранить и показать» opens the result. Parts the type does not use are sent empty, so a
 * switch of the type before the first save leaves no stale part the server would refuse.
 */
define('itvolga:views/report/record/edit', ['views/record/edit'], (EditView) => {

    const PARTS = {
        tabular: ['columns', 'sorting', 'totals', 'calculations'],
        summaries: ['groups', 'aggregates', 'groupSort', 'havingFilters', 'charts'],
        summariesWithDetails: ['groups', 'aggregates', 'groupSort', 'havingFilters', 'columns', 'sorting', 'charts'],
        matrix: ['groups', 'aggregates', 'groupSort', 'havingFilters', 'charts'],
    };
    const EMPTY = {columns: [], sorting: [], totals: [], calculations: [], groups: [], aggregates: [], groupSort: null,
        havingFilters: [], charts: null};

    return class extends EditView {

        saveAndNewAction = false

        setup() {
            super.setup();

            this.buttonList = [
                {name: 'save', label: 'Save and Show', style: 'primary', title: 'Ctrl+Enter'},
                {name: 'saveAndContinueEditing', label: 'Save'},
                {name: 'cancel', label: 'Cancel', title: 'Esc'},
            ];
            this.dropdownItemList = [];

            if (this.model.isNew()) {
                const defaults = {};

                if (this.options.duplicateSourceId) {
                    // A copy belongs to its author and starts private (D-100); the seed key is not copied (duplicateIgnore).
                    defaults.name = (this.model.get('name') || '') + ' ' + this.translate('copySuffix', 'labels', 'Report');
                    defaults.accessType = 'private';
                    defaults.sharedUsersIds = [];
                    defaults.sharedUsersNames = {};
                    defaults.sharedTeamsIds = [];
                    defaults.sharedTeamsNames = {};
                }

                if (!this.getUser().isAdmin() || !this.model.get('assignedUserId') || this.options.duplicateSourceId) {
                    defaults.assignedUserId = this.getUser().id;
                    defaults.assignedUserName = this.getUser().get('name');
                }

                if (!this.model.get('aggregates')) {
                    defaults.aggregates = [{function: 'COUNT', link: null, field: null}];
                }

                this.model.set(defaults);
            }

            this.listenTo(this.model, 'change:entityType', (model, value, options) => {
                if (options.ui && this.model.isNew()) {
                    this.model.set({...EMPTY, aggregates: [{function: 'COUNT', link: null, field: null}],
                        quickFilters: [], filters: {type: 'and', items: []}, labels: {}, dashboard: null});
                }
            });
        }

        fetch() {
            const data = super.fetch();
            const type = this.model.get('type') || data.type;
            const used = PARTS[type] || [];

            Object.keys(EMPTY).forEach(part => {
                if (!used.includes(part)) {
                    data[part] = EMPTY[part];
                }
            });

            return data;
        }
    };
});
