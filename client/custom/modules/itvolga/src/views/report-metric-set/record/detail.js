/**
 * The page of a key-metrics set: its fields and rows, and below them the values for the current user (D-112),
 * refreshed after a save.
 */
define('itvolga:views/report-metric-set/record/detail', ['views/record/detail'], (DetailView) => {

    return class extends DetailView {

        bottomView = 'itvolga:views/report-metric-set/values'

        setup() {
            super.setup();

            this.listenTo(this.model, 'sync', () => {
                const values = this.getView('bottom');

                values && values.isRendered() && values.load();
            });
        }
    };
});
