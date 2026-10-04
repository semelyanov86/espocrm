/**
 * Mass action «Переместить в папку» of the report list: a folder is picked in the standard select dialog, the core
 * mass update sets it on the chosen reports (the server checks edit access to each).
 */
define('itvolga:handlers/report/move-to-folder', [], () => {

    return class {

        constructor(view) {
            this.view = view;
        }

        process(data) {
            this.view.createView('selectFolder', 'views/modals/select-records', {
                entityType: 'ReportFolder',
                multiple: false,
                createButton: false,
                headerText: this.view.translate('Move to Folder', 'labels', 'Report'),
            }, dialog => {
                dialog.render();

                this.view.listenToOnce(dialog, 'select', model => {
                    Espo.Ui.notifyWait();

                    Espo.Ajax.postRequest('MassAction', {
                        entityType: 'Report',
                        action: 'update',
                        params: data.params,
                        data: {folderId: model.id},
                    }).then(() => {
                        Espo.Ui.success(this.view.translate('Done'));
                        this.view.collection.fetch();
                    });
                });
            });
        }
    };
});
