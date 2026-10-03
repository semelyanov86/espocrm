/**
 * «Создать заказ» on a quote, «Создать счёт» on a quote or a sales order, «Создать акт» on an invoice and «Добавить
 * платёж» on an invoice or a sales order (clientDefs detailActionList): opens a new record prefilled by the server
 * (header, lines or the allocation to the source document). Nothing is saved until the user saves the form; the server
 * calculates it. An invoice that already has a live act offers «Открыть акт» instead (the server refuses a second
 * act too); a removed act keeps the invoice's key, but its name is not loaded, so the invoice gets a new act.
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

        createPayment() {
            return this.convert('Payment');
        }

        createAct() {
            return this.convert('Act');
        }

        canCreateAct() {
            return !this.hasAct() && this.view.getAcl().checkModel(this.view.model, 'edit');
        }

        hasAct() {
            const model = this.view.model;

            return !!(model.get('actId') && model.get('actName'));
        }

        openAct() {
            this.view.getRouter().navigate(`#Act/view/${this.view.model.get('actId')}`, {trigger: true});
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
