/**
 * Export of a report result (reports.md §12, D-116, D-120): the format (CSV, XLSX, PDF), the variant — the report data
 * with its limits or all records up to the cap of a run — and «in the background» (the file comes by e-mail and in the
 * notifications). The file is made of the conditions of the shown result (one-off filters, quick filters); the
 * server checks the export permission and the access again. A file is downloaded by the core entry point.
 */
define('itvolga:views/report/modals/export', ['views/modal'], (ModalView) => {

    return class extends ModalView {

        className = 'dialog dialog-record'
        backdrop = true

        templateContent = `
            <div class="row">
                <div class="cell form-group col-sm-6">
                    <label class="control-label">{{formatLabel}}</label>
                    <select class="form-control" data-name="format">
                        {{#each formats}}<option value="{{value}}">{{label}}</option>{{/each}}
                    </select>
                </div>
                <div class="cell form-group col-sm-6">
                    <label class="control-label">{{variantLabel}}</label>
                    <select class="form-control" data-name="variant">
                        {{#each variants}}<option value="{{value}}">{{label}}</option>{{/each}}
                    </select>
                </div>
            </div>
            <div class="cell form-group">
                <div class="checklist-item-container">
                    <input type="checkbox" class="form-checkbox" data-name="background" id="{{cid}}-background">
                    <label for="{{cid}}-background" class="checklist-label">{{backgroundLabel}}</label>
                </div>
            </div>`

        setup() {
            this.headerText = this.translate('Export Report', 'labels', 'Report');
            this.buttonList = [
                {name: 'export', text: this.translate('Export Report', 'labels', 'Report'), style: 'primary'},
                {name: 'cancel', label: 'Cancel'},
            ];
        }

        data() {
            const lang = this.getLanguage();
            const maxRows = this.options.maxRows || 5000;

            return {
                cid: this.cid,
                formatLabel: this.translate('Format', 'labels', 'Report'),
                variantLabel: this.translate('Variant', 'labels', 'Report'),
                backgroundLabel: this.translate('exportBackground', 'labels', 'Report'),
                formats: ['xlsx', 'csv', 'pdf'].map(value =>
                    ({value: value, label: lang.translateOption(value, 'exportFormat', 'Report')})),
                variants: [
                    {value: 'report', label: this.translate('exportVariantReport', 'labels', 'Report')},
                    {value: 'all', label: this.translate('exportVariantAll', 'labels', 'Report')
                        .replace('{n}', String(maxRows))},
                ],
            };
        }

        async actionExport() {
            const value = name => this.element.querySelector(`[data-name="${name}"]`);
            const body = {
                ...this.options.params,
                format: value('format').value,
                variant: value('variant').value,
                background: value('background').checked,
            };

            this.disableButton('export');
            Espo.Ui.notifyWait();

            try {
                const response = await Espo.Ajax.postRequest(`Report/${this.options.reportId}/export`, body);

                if (response.scheduled) {
                    Espo.Ui.success(this.translate('exportScheduled', 'labels', 'Report'));
                } else {
                    Espo.Ui.notify(false);
                    window.location.href = this.getBasePath() + '?entryPoint=download&id=' +
                        encodeURIComponent(response.id);
                }

                this.close();
            } catch (e) {
                // A refused request is reported by the core error handler.
                this.enableButton('export');
            }
        }
    };
});
