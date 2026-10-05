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
                    [{name: 'charts'}, {name: 'dashboard'}],
                    [{name: 'mailing', fullWidth: true}],
                    [{name: 'description', fullWidth: true}],
                ],
            },
        ]

        setup() {
            super.setup();

            // Added to the beginning one by one: «Сформировать», «Экспорт», «Печать».
            if (this.canExport()) {
                this.addButton({name: 'printReport', label: 'Print Report', style: 'default'}, true);
                this.addButton({name: 'exportReport', label: 'Export Report', style: 'default'}, true);
            }

            this.addButton({name: 'runReport', label: 'Run', style: 'default'}, true);
            this.hidePanel('info');
        }

        /**
         * Export and print need the export permission of the role (D-116, D-119), like the core list export; the server
         * checks it again.
         */
        canExport() {
            if (this.getUser().isAdmin()) {
                return true;
            }

            return !this.getConfig().get('exportDisabled') &&
                this.getAcl().getPermissionLevel('exportPermission') === 'yes';
        }

        actionExportReport() {
            const result = this.getView('bottom');

            if (result) {
                result.openOutput('itvolga:views/report/modals/export');
            }
        }

        actionPrintReport() {
            const result = this.getView('bottom');

            if (result) {
                result.openOutput('itvolga:views/report/modals/print');
            }
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
