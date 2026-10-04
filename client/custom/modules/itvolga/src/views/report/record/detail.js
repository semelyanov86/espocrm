/**
 * The page of a report shows its result (reports.md §7): the report info panel (collapsed by default), and below the
 * result view with the conditions, quick filters and the table. «Сформировать» runs the report again.
 */
define('itvolga:views/report/record/detail', ['views/record/detail'], (DetailView) => {

    return class extends DetailView {

        bottomView = 'itvolga:views/report/result'

        // «Изменить» opens the report builder (record/edit); the info panel is a summary, not an editor.
        editModeDisabled = true
        inlineEditDisabled = true

        detailLayout = [
            {
                name: 'info',
                label: 'Report Info',
                rows: [
                    [{name: 'type'}, {name: 'entityType'}],
                    [{name: 'folder'}, {name: 'assignedUser'}],
                    [{name: 'accessType'}, {name: 'rowLimit'}],
                    [{name: 'groups', fullWidth: true}],
                    [{name: 'aggregates'}, {name: 'groupLimit'}],
                    [{name: 'columns'}, {name: 'sorting'}],
                    [{name: 'filters', fullWidth: true}],
                    [{name: 'description', fullWidth: true}],
                ],
            },
        ]

        setup() {
            super.setup();

            this.addButton({name: 'runReport', label: 'Run', style: 'default'}, true);
            this.hidePanel('info');
        }

        actionRunReport() {
            const result = this.getView('bottom');

            if (result) {
                // From the first page: the conditions may have changed since a later page was shown.
                result.run(true);
            }
        }

        toggleInfo() {
            this.infoShown = !this.infoShown;
            this.infoShown ? this.showPanel('info') : this.hidePanel('info');
        }
    };
});
