/**
 * «Печать» on a finance record (stage 05, clientDefs detailActionList): opens the record's print form — a PDF made by
 * the server (?entryPoint=itvolgaPrint) — in a new tab. A form with a condition (metadata
 * app.itvolgaFinance.printForms.<entityType>.onlyWhen: the cash receipt order of incoming payments) is offered only when
 * the record meets it; the server checks access and the condition again.
 */
define('itvolga:handlers/finance/print-form', [], () => {

    return class {

        /**
         * @param {import('views/record/detail').default} view
         */
        constructor(view) {
            this.view = view;
        }

        canPrint() {
            const model = this.view.model;
            const onlyWhen = this.view.getMetadata()
                .get(['app', 'itvolgaFinance', 'printForms', model.entityType, 'onlyWhen']) || {};

            return Object.entries(onlyWhen).every(([attribute, value]) => model.get(attribute) === value);
        }

        print() {
            const model = this.view.model;
            const params = new URLSearchParams({entryPoint: 'itvolgaPrint', entityType: model.entityType, id: model.id});

            window.open('?' + params.toString(), '_blank');
        }
    };
});
