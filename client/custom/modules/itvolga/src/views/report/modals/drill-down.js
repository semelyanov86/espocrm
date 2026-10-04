/**
 * Records of a report group (drill-down, D-98): the standard record list of the main entity in a modal, filtered by the
 * where item `itvolgaReport` — the server selects the records with the report's own query (its conditions, the
 * one-off conditions and quick filters of the run, the ACL of the user) plus the keys of the group.
 */
define('itvolga:views/report/modals/drill-down', ['views/modal'], (ModalView) => {

    return class extends ModalView {

        className = 'dialog dialog-record'
        templateContent = `<div class="list-container">{{{list}}}</div>`
        backdrop = true

        setup() {
            this.headerText = this.translate('Group records', 'labels', 'Report');
            this.buttonList = [{name: 'cancel', label: 'Close'}];
            const entityType = this.options.entityType;

            this.wait(this.getCollectionFactory().create(entityType).then(collection => {
                collection.maxSize = this.getConfig().get('recordsPerPage') || 20;
                collection.where = [{
                    type: 'itvolgaReport',
                    attribute: 'id',
                    value: JSON.stringify({
                        id: this.options.reportId,
                        path: this.options.path,
                        filters: this.options.filters || null,
                        quickFilters: this.options.quickFilters || [],
                    }),
                }];
                this.collection = collection;

                return this.createView('list', 'views/record/list', {
                    collection: collection,
                    selector: '.list-container',
                    checkboxes: false,
                    massActionsDisabled: true,
                    rowActionsView: 'views/record/row-actions/view-only',
                    pagination: true,
                    displayTotalCount: true,
                    skipBuildRows: true,
                }).then(view => view.getSelectAttributeList().then(attributes => {
                    if (attributes) {
                        collection.data.select = attributes.join(',');
                    }

                    return collection.fetch();
                }));
            }));
        }
    };
});
