/**
 * The call card (popup notification itvolgaCall, stage 07.1 D-170): who is calling, the clients of the number the
 * user may see, the Call and «create a contact / lead» for an unknown number. The listener decides the state; the
 * card follows it on every poll (update-data). A closed card goes away without a sound; a card the server stopped
 * sending (closed on another device, expired) goes away after 20 s and comes back if the server sends it again;
 * closing it with ✕ dismisses it on the server until the call becomes active for this user again.
 */
define('itvolga:views/telephony/call-card', ['views/popup-notification'], (PopupNotificationView) => {

    const STALE_MS = 20000;
    /**
     * Card id → the state it had when closed or dismissed in this tab: the core manager hands a card it already
     * removed again on the next poll (its closed-id check compares another id). Only the same state stays hidden.
     */
    const gone = new Map();

    return class extends PopupNotificationView {

        type = 'itvolgaCall';
        style = 'primary';
        closeButton = true;
        collapseButton = true;

        templateContent = `
            {{#unless gone}}
            {{#if closeButton~}}
                <a role="button" tabindex="0" class="pull-right close" data-action="close" aria-hidden="true"
                    title="{{translate 'Close'}}"><span class="fas fa-times"></span></a>
            {{~/if~}}
            {{#if collapseButton~}}
                <a role="button" tabindex="0" class="pull-right text-muted" data-action="collapse" aria-hidden="true"
                    title="{{translate 'Collapse'}}"><span class="fas fa-minus"></span></a>
            {{~/if}}
            <h4 data-role="header"><span class="fas fa-phone-alt"></span> {{header}}</h4>
            <div class="cell form-group">
                <div class="field">
                    <span data-role="number" class="text-bold">{{number}}</span>
                    <span data-role="state" class="label label-{{stateStyle}}" style="margin-left: 0.5em;">{{stateLabel}}</span>
                </div>
                {{#if hint}}<div class="small text-muted" data-role="hint">{{hint}}</div>{{/if}}
            </div>
            <div class="cell form-group" data-role="clients">
                {{#each clients}}
                    <div>
                        <a href="#{{entityType}}/view/{{id}}" data-action="close">{{name}}</a>
                        {{#if accountName}}<span class="text-muted small">({{accountName}})</span>{{/if}}
                        {{#if possible}}<span class="label label-default">{{../possibleLabel}}</span>{{/if}}
                    </div>
                {{else}}
                    <div class="text-muted">{{noClientLabel}}</div>
                {{/each}}
            </div>
            <div class="cell" data-role="actions">
                {{#if call}}<a href="#Call/view/{{call.id}}" class="btn btn-default btn-sm" data-action="close"
                    data-role="open-call">{{translate 'Open call' scope='Call'}}</a>{{/if}}
                {{#if canCreateContact}}<button type="button" class="btn btn-default btn-sm"
                    data-action="createClient" data-scope="Contact">{{translate 'Create Contact' scope='Call'}}</button>{{/if}}
                {{#if canCreateLead}}<button type="button" class="btn btn-default btn-sm"
                    data-action="createClient" data-scope="Lead">{{translate 'Create Lead' scope='Call'}}</button>{{/if}}
            </div>
            {{/unless}}`

        setup() {
            const state = (this.notificationData || {}).state;
            this.gone = state === 'closed' || gone.get(this.notificationId) === state;
            this.touchedAt = Date.now();

            this.addActionHandler('createClient', (event, target) => this.createClient(target.dataset.scope));

            this.on('update-data', data => {
                this.touchedAt = Date.now();
                this.notificationData = data || {};

                if (this.notificationData.state === 'closed') {
                    this.goAway(true);

                    return;
                }

                if (!this.isCollapsed) {
                    this.reRender();
                }
            });

            this.staleTimer = setInterval(() => {
                if (Date.now() - this.touchedAt > STALE_MS) {
                    this.goAway(false);
                }
            }, 5000);

            this.once('remove', () => clearInterval(this.staleTimer));
        }

        data() {
            const d = this.notificationData || {};
            const inbound = d.direction === 'Inbound';
            const states = {
                ringing: ['Ringing', 'warning'],
                dialing: ['Dialing', 'info'],
                talking: ['Talking', 'success'],
                ended: ['Ended', 'default'],
            };
            const [stateKey, stateStyle] = states[d.state] || ['Ended', 'default'];
            let header = this.translate(inbound ? 'Incoming call' : 'Outgoing call', 'labels', 'Call');

            if (d.viaCrm) {
                header = this.translate('Call from CRM', 'labels', 'Call');
            }

            return {
                ...super.data(),
                gone: this.gone,
                header: header,
                number: d.number || this.translate('Hidden number', 'labels', 'Call'),
                stateLabel: this.translate(stateKey, 'labels', 'Call'),
                stateStyle: stateStyle,
                hint: d.viaCrm && d.state === 'dialing' && !d.call ? this.translate('Pick up the phone', 'labels', 'Call') : null,
                clients: d.clients || [],
                possibleLabel: this.translate('Possible match', 'labels', 'Call'),
                noClientLabel: this.translate('No client found', 'labels', 'Call'),
                call: d.call || null,
                canCreateContact: Boolean(d.canCreateContact) && Boolean(d.number),
                canCreateLead: Boolean(d.canCreateLead) && Boolean(d.number),
            };
        }

        onShow() {
            if (this.gone) {
                setTimeout(() => this.goAway(true), 0);

                return;
            }

            const d = this.notificationData || {};

            if (d.direction === 'Inbound' && d.state === 'ringing') {
                super.onShow();
            }
        }

        onCancel() {
            gone.set(this.notificationId, (this.notificationData || {}).state);
            Espo.Ajax.postRequest(`Telephony/cards/${encodeURIComponent(this.notificationId)}/dismiss`, {});
        }

        /**
         * @param {boolean} remember keep it hidden while the server sends the same state (closed); a stale card is
         *     only removed and shows again when the server sends it again
         */
        goAway(remember) {
            if (remember) {
                gone.set(this.notificationId, (this.notificationData || {}).state || 'closed');
            }

            if (!this.isRemoved()) {
                this.remove();
            }
        }

        createClient(entityType) {
            const number = (this.notificationData || {}).number;

            // The form belongs to the notification badge, not to this card: the card may go away while the user types.
            const owner = this.getParentView() || this;

            Espo.loader.requirePromise('helpers/record-modal').then(RecordModal => {
                new RecordModal().showCreate(owner, {entityType: entityType, attributes: {phoneNumber: number}});
            });
        }

        getTitle() {
            return (this.notificationData || {}).number || this.translate('Hidden number', 'labels', 'Call');
        }
    };
});
