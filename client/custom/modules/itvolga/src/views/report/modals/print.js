/**
 * Print view of a report result (reports.md §12, D-119): the server makes the page — the title, the counters and the
 * limit notes, the table as on the screen with all rows within the report limits, the totals; no charts — of the
 * conditions of the shown result and checks the export permission. It is shown in a sandboxed frame (no scripts) and
 * printed by the browser from there.
 */
define('itvolga:views/report/modals/print', ['views/modal'], (ModalView) => {

    return class extends ModalView {

        className = 'dialog dialog-record'
        backdrop = true
        templateContent = `<iframe class="itv-report-print" data-role="print-frame" width="100%" height="400"
            sandbox="allow-same-origin allow-modals" title="{{title}}"></iframe>`

        setup() {
            this.headerText = this.translate('Print Report', 'labels', 'Report');
            this.buttonList = [
                {name: 'print', text: this.translate('Print', 'labels', 'Report'), style: 'primary'},
                {name: 'cancel', label: 'Close'},
            ];

            this.wait(
                Espo.Ajax.postRequest(`Report/${this.options.reportId}/printView`, {...this.options.params})
                    .then(view => this.printView = view)
            );
        }

        data() {
            return {title: this.printView.title};
        }

        frame() {
            return this.element.querySelector('[data-role="print-frame"]');
        }

        afterRender() {
            const frame = this.frame();

            frame.addEventListener('load', () => {
                // The frame grows with the page, up to most of the window.
                const height = frame.contentDocument ? frame.contentDocument.documentElement.scrollHeight : 400;
                frame.height = String(Math.min(height + 20, Math.round(window.innerHeight * 0.7)));
            });

            frame.srcdoc = this.printView.html;
        }

        actionPrint() {
            const frame = this.frame();

            frame.contentWindow.focus();
            frame.contentWindow.print();
        }
    };
});
