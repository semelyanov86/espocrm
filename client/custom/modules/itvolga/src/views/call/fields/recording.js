/**
 * «Запись разговора» of a Call (stage 07.1, D-171): the player of the recording of a finished telephony call. The
 * audio comes from ?entryPoint=itvolgaRecording (authenticated, access to the call and to this field checked, every
 * playback logged); nothing is loaded before Play. A role that forbids the field never gets it at all.
 */
define('itvolga:views/call/fields/recording', ['views/fields/bool'], (BoolFieldView) => {

    return class extends BoolFieldView {

        detailTemplateContent = `
            {{#if playable}}
                <audio controls preload="none" data-role="player" src="{{src}}" style="width: 100%; max-width: 32em;"></audio>
            {{else}}
                <span class="text-muted" data-role="no-recording">{{text}}</span>
            {{/if}}`

        listTemplateContent = `{{#if value}}<span class="fas fa-volume-up text-muted" title="{{title}}"></span>{{/if}}`

        setup() {
            super.setup();

            this.listenTo(this.model, 'change:cRecording change:cLiveState', () => {
                if (this.isRendered() && !this.isEditMode()) {
                    this.reRender();
                }
            });
        }

        data() {
            const live = ['ringing', 'talking'].includes(this.model.get('cLiveState'));
            const playable = Boolean(this.model.get('cRecording')) && !live && Boolean(this.model.id);

            return {
                ...super.data(),
                playable: playable,
                src: '?' + new URLSearchParams({entryPoint: 'itvolgaRecording', id: this.model.id || ''}).toString(),
                text: this.translate(live ? 'Recording is being written' : 'Recording is not available', 'labels', 'Call'),
                title: this.translate('cRecording', 'fields', 'Call'),
            };
        }
    };
});
