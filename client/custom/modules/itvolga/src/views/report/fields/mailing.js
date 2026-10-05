/**
 * Step 9 «Рассылка» of the builder (reports.md §13, D-121): on/off; the frequency with only its own fields (weekday for
 * weekly and every two weeks, day of month for monthly, month and day for yearly) and the time on the 15-minute grid of
 * the job, in the owner's time zone; the next run computed by the server as the settings change; the letter (subject,
 * text), the formats, «no limit», «skip an empty report»; the recipients — users and teams (core link-multiple fields)
 * and other addresses — or «generate for» (user links of the report; each found user gets his own slice).
 *
 * The stored part is never read back by the API (`internal`): the editor starts from `mailingSettings`, which only an
 * owner or an administrator gets in full. The part is sent with the form only when it was changed here (typing counts),
 * so a save of other steps never writes back settings loaded earlier over a newer change (internal review). In the detail view — a summary; a reader who may not edit the report
 * sees only when the letters go.
 */
define('itvolga:views/report/fields/mailing', ['itvolga:views/report/fields/base'], (BaseView) => {

    const FREQUENCIES = ['daily', 'weekly', 'biweekly', 'monthly', 'yearly'];
    const FORMATS = ['xlsx', 'csv', 'pdf'];
    const TIMES = [];

    for (let h = 0; h < 24; h++) {
        ['00', '15', '30', '45'].forEach(m => TIMES.push(String(h).padStart(2, '0') + ':' + m));
    }

    return class extends BaseView {

        dependsOn = ['assignedUserId']

        detailTemplateContent = `
            {{#if enabled}}
                <div>{{schedule}}{{#if formats}} · {{formats}}{{/if}}</div>
                {{#if recipients}}<div class="text-muted small">{{recipients}}</div>{{/if}}
                {{#if nextRun}}<div class="small">{{nextRunLabel}}: {{nextRun}}</div>{{/if}}
                {{#if lastRun}}<div class="small text-muted">{{lastRunLabel}}: {{lastRun}}</div>{{/if}}
            {{else}}<span class="none-value">{{offLabel}}</span>{{/if}}`

        editTemplateContent = `
            <div class="cell form-group">
                <div class="checklist-item-container"><input type="checkbox" class="form-checkbox" data-key="enabled"
                    id="{{cid}}-enabled" {{#if state.enabled}}checked{{/if}}><label for="{{cid}}-enabled" class="checklist-label">{{t.enabled}}</label></div>
            </div>
            <div class="row">
                <div class="cell form-group col-sm-3"><label class="control-label small">{{t.frequency}}</label>
                    <select class="form-control input-sm" data-key="frequency">
                        {{#each frequencies}}<option value="{{value}}" {{#if selected}}selected{{/if}}>{{label}}</option>{{/each}}
                    </select></div>
                <div class="cell form-group col-sm-2"><label class="control-label small">{{t.time}}</label>
                    <select class="form-control input-sm" data-key="time">
                        {{#each times}}<option value="{{value}}" {{#if selected}}selected{{/if}}>{{value}}</option>{{/each}}
                    </select></div>
                {{#if showWeekday}}<div class="cell form-group col-sm-3"><label class="control-label small">{{t.weekday}}</label>
                    <select class="form-control input-sm" data-key="weekday" data-number="1">
                        {{#each weekdays}}<option value="{{value}}" {{#if selected}}selected{{/if}}>{{label}}</option>{{/each}}
                    </select></div>{{/if}}
                {{#if showMonth}}<div class="cell form-group col-sm-3"><label class="control-label small">{{t.month}}</label>
                    <select class="form-control input-sm" data-key="month" data-number="1">
                        {{#each months}}<option value="{{value}}" {{#if selected}}selected{{/if}}>{{label}}</option>{{/each}}
                    </select></div>{{/if}}
                {{#if showDay}}<div class="cell form-group col-sm-2"><label class="control-label small">{{t.day}}</label>
                    <select class="form-control input-sm" data-key="day" data-number="1">
                        {{#each days}}<option value="{{value}}" {{#if selected}}selected{{/if}}>{{value}}</option>{{/each}}
                    </select></div>{{/if}}
            </div>
            <div class="small" data-role="next-run"></div>
            <div class="small text-muted">{{t.timeHint}}</div>
            <div class="row">
                <div class="cell form-group col-sm-6"><label class="control-label small">{{t.subject}}</label>
                    <input type="text" class="form-control input-sm" data-key="subject" maxlength="255"
                        value="{{state.subject}}" placeholder="{{t.subjectPlaceholder}}"></div>
                <div class="cell form-group col-sm-6"><label class="control-label small">{{t.formats}}</label>
                    <div>{{#each formats}}<div class="checklist-item-container"><input type="checkbox"
                        class="form-checkbox" data-format="{{value}}" id="{{../cid}}-format-{{value}}"
                        {{#if selected}}checked{{/if}}><label for="{{../cid}}-format-{{value}}"
                        class="checklist-label">{{label}}</label></div>{{/each}}</div></div>
            </div>
            <div class="cell form-group"><label class="control-label small">{{t.text}}</label>
                <textarea class="form-control input-sm" rows="3" data-key="text" maxlength="5000"
                    placeholder="{{t.textPlaceholder}}">{{state.text}}</textarea></div>
            <div class="cell form-group">
                <div class="checklist-item-container"><input type="checkbox" class="form-checkbox" data-key="noLimit"
                    id="{{cid}}-no-limit" {{#if state.noLimit}}checked{{/if}}><label for="{{cid}}-no-limit" class="checklist-label">{{t.noLimit}}</label></div>
                <div class="checklist-item-container"><input type="checkbox" class="form-checkbox" data-key="skipEmpty"
                    id="{{cid}}-skip-empty" {{#if state.skipEmpty}}checked{{/if}}><label for="{{cid}}-skip-empty" class="checklist-label">{{t.skipEmpty}}</label></div>
            </div>
            <div class="cell form-group"><label class="control-label small">{{t.generateFor}}</label>
                <div class="small text-muted">{{t.generateForHint}}</div>
                <div>{{#each generateFor}}<div class="checklist-item-container"><input type="checkbox"
                    class="form-checkbox" data-generate-for="{{value}}" id="{{../cid}}-for-{{@index}}"
                    {{#if selected}}checked{{/if}}><label for="{{../cid}}-for-{{@index}}"
                    class="checklist-label">{{label}}</label></div>{{/each}}
                    {{#unless generateFor}}<span class="text-muted small">—</span>{{/unless}}</div></div>
            {{#unless personal}}
            <div class="cell form-group"><label class="control-label small">{{t.recipients}}</label>
                <div class="small text-muted">{{t.recipientsHint}}</div></div>
            <div class="row">
                <div class="cell form-group col-sm-4"><label class="control-label small">{{t.users}}</label>
                    <div class="field" data-role="users"></div></div>
                <div class="cell form-group col-sm-4"><label class="control-label small">{{t.teams}}</label>
                    <div class="field" data-role="teams"></div></div>
                <div class="cell form-group col-sm-4"><label class="control-label small">{{t.emails}}</label>
                    <input type="text" class="form-control input-sm" data-key="emails" value="{{emails}}"></div>
            </div>
            {{/unless}}
            {{#if lastRun}}<div class="small text-muted">{{t.lastRun}}: {{lastRun}}</div>{{/if}}`

        emptyValue() {
            return {enabled: false, frequency: 'daily', time: '09:00', weekday: 1, day: 1, month: 1, subject: '',
                text: '', users: [], teams: [], emails: [], formats: ['xlsx'], noLimit: false, skipEmpty: false,
                generateFor: []};
        }

        setup() {
            this.names = {users: {}, teams: {}};
            this.touched = false;
            this.previewGeneration = 0;
            super.setup();

            // Typing marks the part changed at once: a save by a shortcut comes without a change event.
            this.addHandler('input', 'input[data-key], textarea[data-key]', () => this.touched = true);

            this.addHandler('change', '[data-key]', (e, target) => {
                const key = target.dataset.key;
                const value = target.type === 'checkbox' ? target.checked :
                    target.dataset.number ? Number(target.value) : target.value;

                this.state[key] = key === 'emails' ? this.parseEmails(value) : value;
                this.touch(['enabled', 'frequency'].includes(key));
            });

            this.addHandler('change', '[data-format]', () => {
                this.state.formats = FORMATS.filter(format =>
                    this.element.querySelector(`[data-format="${format}"]`).checked);
                this.touch(false);
            });

            this.addHandler('change', '[data-generate-for]', () => {
                this.state.generateFor = [...this.element.querySelectorAll('[data-generate-for]')]
                    .filter(input => input.checked).map(input => input.dataset.generateFor);

                if (this.state.generateFor.length) {
                    // «Generate for» excludes the recipients (D-122).
                    Object.assign(this.state, {users: [], teams: [], emails: []});
                    this.names = {users: {}, teams: {}};
                }

                this.touch(true);
            });

            this.wait(this.getModelFactory().create('Report').then(model => {
                // A helper model gives the core link-multiple fields of users and teams.
                this.recipientModel = model;
                this.listenTo(model, 'change:sharedUsersIds change:sharedTeamsIds', () => {
                    this.state.users = [...(model.get('sharedUsersIds') || [])];
                    this.state.teams = [...(model.get('sharedTeamsIds') || [])];
                    this.names = {users: {...(model.get('sharedUsersNames') || {})},
                        teams: {...(model.get('sharedTeamsNames') || {})}};
                    this.touch(false);
                });
            }));
        }

        /**
         * The editor of an owner or an administrator starts from the whole stored part; it is sent back only when
         * changed here (fetch).
         */
        readState() {
            const settings = this.model.get('mailingSettings');
            this.full = !!settings && Array.isArray(settings.users);
            this.lastRunAt = null;
            this.lastResult = null;

            if (!this.full) {
                return this.emptyValue();
            }

            const state = {...this.emptyValue(), ...JSON.parse(JSON.stringify(settings))};
            this.names = state.names || {users: {}, teams: {}};
            this.lastRunAt = state.lastRunAt || null;
            this.lastResult = state.lastResult || null;
            ['names', 'lastRunAt', 'lastResult'].forEach(key => delete state[key]);
            ['weekday', 'day', 'month'].forEach(key => state[key] = state[key] ?? 1);

            return state;
        }

        touch(reRender) {
            this.touched = true;
            this.commit(reRender);
            this.preview();
        }

        parseEmails(text) {
            return String(text || '').split(/[;,\s]+/).map(s => s.trim()).filter(Boolean);
        }

        onDependencyChange() {
            this.preview();
        }

        fetch() {
            if (!this.touched) {
                return {};
            }

            if (this.isEditMode() && this.isRendered() && !this.domStale) {
                // Texts are taken from the inputs: a save by a shortcut comes without a change event.
                ['subject', 'text', 'emails'].forEach(key => {
                    const input = this.element.querySelector(`[data-key="${key}"]`);

                    if (input) {
                        this.state[key] = key === 'emails' ? this.parseEmails(input.value) : input.value;
                    }
                });
            }

            const state = JSON.parse(JSON.stringify(this.state));

            if (!['weekly', 'biweekly'].includes(state.frequency)) {
                state.weekday = null;
            }

            if (!['monthly', 'yearly'].includes(state.frequency)) {
                state.day = null;
            }

            if (state.frequency !== 'yearly') {
                state.month = null;
            }

            return {[this.name]: state};
        }

        lastRunText() {
            if (!this.lastRunAt) {
                return null;
            }

            const result = this.lastResult || {};
            const lang = this.getLanguage();
            const parts = [lang.translateOption(result.status || 'running', 'mailingStatus', 'Report')];

            if (result.error) {
                parts.push(lang.translateOption(result.error, 'mailingError', 'Report'));
            }

            if (result.letters) {
                parts.push(`${this.translateReport('Letters')}: ${result.letters}`);
                ['sent', 'noSmtp', 'failed'].filter(key => result[key]).forEach(key => parts.push(
                    this.translateReport('lastResult' + key.charAt(0).toUpperCase() + key.slice(1)) + ': ' +
                    result[key]));
            }

            Object.entries(result.skipped || {}).forEach(([reason, n]) => parts.push(
                this.translateReport('lastResultSkipped') + ' (' + lang.translateOption(reason, 'mailingSkip',
                    'Report') + '): ' + n));

            if (result.pdfTooLarge) {
                parts.push(this.translateReport('lastResultPdfTooLarge'));
            }

            if (result.capped) {
                parts.push(this.translateReport('lastResultCapped'));
            }

            return this.getDateTime().toDisplay(this.lastRunAt) + ' — ' + parts.join('; ');
        }

        scheduleText(settings) {
            const lang = this.getLanguage();
            const parts = [lang.translateOption(settings.frequency, 'mailingFrequency', 'Report')];
            const dayNames = lang.get('Global', 'lists', 'dayNames') || [];
            const monthNames = lang.get('Global', 'lists', 'monthNames') || [];

            if (['weekly', 'biweekly'].includes(settings.frequency)) {
                parts.push(String(dayNames[settings.weekday % 7] || settings.weekday).toLowerCase());
            }

            if (settings.frequency === 'monthly') {
                parts.push(this.translateReport('mailingDayOfMonth').replace('{n}', settings.day));
            }

            if (settings.frequency === 'yearly') {
                parts.push(settings.day + ' ' + String(monthNames[settings.month - 1] || settings.month).toLowerCase());
            }

            parts.push(settings.time);

            return parts.join(', ');
        }

        data() {
            const lang = this.getLanguage();
            const settings = this.model.get('mailingSettings') || null;

            if (!this.isEditMode()) {
                const enabled = !!settings && settings.enabled;
                let recipients = null;

                if (enabled && this.full) {
                    recipients = settings.generateFor.length ?
                        this.translateReport('Generate for') + ': ' + settings.generateFor.map(r => this.label(r)).join(', ') :
                        [...Object.values(settings.names.users || {}), ...Object.values(settings.names.teams || {}),
                            ...settings.emails].join(', ');
                }

                const next = this.model.get('mailingNextRunAt');

                return {
                    enabled: enabled,
                    schedule: enabled ? this.scheduleText(settings) : null,
                    formats: enabled ? (settings.formats || []).map(f => lang.translateOption(f, 'exportFormat', 'Report'))
                        .join(', ') : null,
                    recipients: recipients,
                    nextRun: next ? this.getDateTime().toDisplay(next) : null,
                    lastRun: this.full ? this.lastRunText() : null,
                    nextRunLabel: this.translateReport('Next run'),
                    lastRunLabel: this.translateReport('Last run'),
                    offLabel: this.translateReport('mailingOff'),
                };
            }

            const state = this.state;
            const dayNames = lang.get('Global', 'lists', 'dayNames') || [];
            const monthNames = lang.get('Global', 'lists', 'monthNames') || [];
            const userLinks = this.fieldOptions(field => field.family === 'link' &&
                field.foreignEntityType === 'User' && field.linkKind !== 'many', null);

            return {
                cid: this.cid,
                state: state,
                personal: state.generateFor.length > 0,
                emails: state.emails.join('; '),
                showWeekday: ['weekly', 'biweekly'].includes(state.frequency),
                showDay: ['monthly', 'yearly'].includes(state.frequency),
                showMonth: state.frequency === 'yearly',
                frequencies: FREQUENCIES.map(value => ({value: value, selected: value === state.frequency,
                    label: lang.translateOption(value, 'mailingFrequency', 'Report')})),
                times: TIMES.map(value => ({value: value, selected: value === state.time})),
                weekdays: [1, 2, 3, 4, 5, 6, 7].map(value => ({value: value, selected: value === state.weekday,
                    label: dayNames[value % 7] || value})),
                months: monthNames.map((label, i) => ({value: i + 1, label: label, selected: i + 1 === state.month})),
                days: Array.from({length: 31}, (v, i) => ({value: i + 1, selected: i + 1 === state.day})),
                formats: FORMATS.map(value => ({value: value, selected: state.formats.includes(value),
                    label: lang.translateOption(value, 'exportFormat', 'Report')})),
                generateFor: userLinks.map(option => ({...option, selected: state.generateFor.includes(option.value)})),
                lastRun: this.lastRunText(),
                t: {
                    enabled: this.translateReport('mailingEnabled'),
                    frequency: this.translateReport('Frequency'),
                    time: this.translateReport('Time'),
                    weekday: this.translateReport('Weekday'),
                    day: this.translateReport('Day of month'),
                    month: this.translateReport('Month'),
                    timeHint: this.translateReport('mailingTimeHint'),
                    subject: this.translateReport('Subject'),
                    subjectPlaceholder: this.translateReport('subjectPlaceholder'),
                    text: this.translateReport('Text'),
                    textPlaceholder: this.translateReport('textPlaceholder'),
                    formats: this.translateReport('Formats'),
                    noLimit: this.translateReport('mailingNoLimit'),
                    skipEmpty: this.translateReport('mailingSkipEmpty'),
                    generateFor: this.translateReport('Generate for'),
                    generateForHint: this.translateReport('generateForHint'),
                    recipients: this.translateReport('Recipients'),
                    recipientsHint: this.translateReport('recipientsHint'),
                    users: this.translateReport('Users'),
                    teams: this.translateReport('Teams'),
                    emails: this.translateReport('Other addresses'),
                    lastRun: this.translateReport('Last run'),
                },
            };
        }

        async afterRender() {
            super.afterRender();

            if (!this.isEditMode()) {
                return;
            }

            this.preview();

            if (this.state.generateFor.length || !this.recipientModel) {
                return;
            }

            this.recipientModel.set({
                sharedUsersIds: [...this.state.users], sharedUsersNames: {...this.names.users},
                sharedTeamsIds: [...this.state.teams], sharedTeamsNames: {...this.names.teams},
            }, {silent: true});

            for (const [key, field] of [['users', 'sharedUsers'], ['teams', 'sharedTeams']]) {
                this.clearView(key);
                const view = await this.createView(key, 'views/fields/link-multiple', {
                    selector: `[data-role="${key}"]`,
                    model: this.recipientModel,
                    name: field,
                    mode: 'edit',
                });

                if (this.isRemoved()) {
                    view.remove();

                    return;
                }

                await view.render();
            }
        }

        /**
         * «Следующий запуск»: the server computes it with the schedule the save uses (owner's time zone).
         */
        preview() {
            const box = this.isEditMode() && this.element ? this.element.querySelector('[data-role="next-run"]') : null;

            if (!box) {
                return;
            }

            if (!this.state.enabled) {
                box.textContent = this.translateReport('mailingOff');

                return;
            }

            const generation = ++this.previewGeneration;
            clearTimeout(this.previewTimer);

            this.previewTimer = setTimeout(async () => {
                const schedule = this.fetch()[this.name] || this.state;

                try {
                    const response = await Espo.Ajax.postRequest('Report/mailingPreview', {
                        assignedUserId: this.model.get('assignedUserId'),
                        mailing: {enabled: true, frequency: schedule.frequency, time: schedule.time,
                            weekday: schedule.weekday, day: schedule.day, month: schedule.month,
                            formats: ['csv'], emails: ['preview@example.com']},
                    });

                    if (generation !== this.previewGeneration || this.isRemoved()) {
                        return;
                    }

                    box.textContent = response.error || (this.translateReport('Next run') + ': ' + response.text);
                } catch (e) {
                    // A refused request is reported by the core.
                }
            }, 300);
        }
    };
});
