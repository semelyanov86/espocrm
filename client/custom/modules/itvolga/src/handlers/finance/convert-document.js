/**
 * «Создать заказ» on a quote and «Создать счёт» on a quote or a sales order (clientDefs detailActionList): opens a new
 * document prefilled by the server (header, lines, link to the source document). Nothing is saved until the user
 * saves the form; the server calculates it.
 */
define('itvolga:handlers/finance/convert-document', [], () => {

    return class {

        /**
         * @param {import('views/record/detail').default} view
         */
        constructor(view) {
            this.view = view;
        }

        createSalesOrder() {
            return this.convert('SalesOrder');
        }

        createInvoice() {
            return this.convert('Invoice');
        }

        /**
         * @param {string} target
         */
        async convert(target) {
            const model = this.view.model;
            const url = `FinanceDocument/${model.entityType}/${model.id}/convertTo/${target}`;

            Espo.Ui.notifyWait();

            const attributes = await Espo.Ajax.getRequest(url);

            Espo.Ui.notify();

            const router = this.view.getRouter();

            router.dispatch(target, 'create', {
                attributes: attributes,
                returnUrl: `#${model.entityType}/view/${model.id}`,
            });
            router.navigate(`#${target}/create`, {trigger: false});
        }
    };
});
