/**
 * «Создать заказ» on a quote (clientDefs.Quote.detailActionList): opens a new sales order prefilled by the server
 * (header, lines, link to the quote). Nothing is saved until the user saves the form; the server calculates it.
 */
define('itvolga:handlers/finance/create-sales-order', [], () => {

    return class {

        /**
         * @param {import('views/record/detail').default} view
         */
        constructor(view) {
            this.view = view;
        }

        async process() {
            const model = this.view.model;
            const url = `FinanceDocument/${model.entityType}/${model.id}/convertTo/SalesOrder`;

            Espo.Ui.notifyWait();

            const attributes = await Espo.Ajax.getRequest(url);

            Espo.Ui.notify();

            const router = this.view.getRouter();

            router.dispatch('SalesOrder', 'create', {
                attributes: attributes,
                returnUrl: `#${model.entityType}/view/${model.id}`,
            });
            router.navigate('#SalesOrder/create', {trigger: false});
        }
    };
});
