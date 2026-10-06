<div class="itv-login" data-step="second"{{#if isDark}} data-dark="true"{{/if}}>
    <section class="itv-login__brand">{{{brand}}}</section>
    <main class="itv-login__side">
        <div id="login" class="itv-login__panel">
            <h1 class="itv-login__title">Подтверждение входа</h1>
            <p class="itv-login__hint">{{message}}</p>
            <div class="panel-body">
                {{#if hasKeys}}
                <div class="itv-login__key-card" data-role="key-card">
                    <svg class="itv-login__key" viewBox="0 0 64 64" focusable="false" aria-hidden="true">
                        <rect class="itv-login__key-body" x="14" y="4" width="36" height="42" rx="8"/>
                        <rect class="itv-login__key-plug" x="22" y="46" width="20" height="14" rx="2"/>
                        <circle class="itv-login__key-touch" cx="32" cy="25" r="8"/>
                    </svg>
                    {{#if isInsecure}}
                    <p class="itv-login__status" data-kind="error">{{translate 'itvolgaSecurityKeyInsecure' category='messages'}}</p>
                    {{else}}
                    <p class="itv-login__status" data-role="status" role="status" aria-live="polite"></p>
                    {{/if}}
                </div>
                {{/if}}
                <div class="cell itv-login__actions">
                    {{#if canUseKey}}
                    <button
                        type="button"
                        class="btn btn-primary itv-login__submit"
                        id="btn-send"
                        data-action="useKey"
                    >{{translate 'itvolgaSecurityKeyUse'}}</button>
                    {{/if}}
                    <a
                        role="button"
                        tabindex="0"
                        class="btn btn-link btn-text btn-text-hoverable btn-sm"
                        data-action="backToLogin"
                    >{{translate 'Back to login form' scope='User'}}</a>
                </div>
            </div>
        </div>
    </main>
</div>
<footer class="itv-login-footer"{{#if isDark}} data-dark="true"{{/if}}>{{{footer}}}</footer>
