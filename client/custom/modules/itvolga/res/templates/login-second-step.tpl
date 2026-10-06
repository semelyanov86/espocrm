<div class="itv-login" data-step="second"{{#if isDark}} data-dark="true"{{/if}}>
    <section class="itv-login__brand">{{{brand}}}</section>
    <main class="itv-login__side">
        <div id="login" class="itv-login__panel">
            <h1 class="itv-login__title">Подтверждение входа</h1>
            <p class="itv-login__hint">{{message}}</p>
            <div class="panel-body">
                <form id="login-form">
                    <div class="form-group cell">
                        <label for="field-code">{{translate 'Code' scope='User'}}</label>
                        <input
                            type="text"
                            data-name="field-code"
                            id="field-code"
                            class="form-control"
                            autocapitalize="off"
                            spellcheck="false"
                            tabindex="1"
                            autocomplete="one-time-code"
                            inputmode="numeric"
                            maxlength="7"
                        >
                    </div>
                    <div class="cell itv-login__actions">
                        <button
                            type="submit"
                            class="btn btn-primary itv-login__submit"
                            id="btn-send"
                            tabindex="2"
                        >{{translate 'Submit'}}</button>
                        <a
                            role="button"
                            tabindex="3"
                            class="btn btn-link btn-text btn-text-hoverable btn-sm"
                            data-action="backToLogin"
                        >{{translate 'Back to login form' scope='User'}}</a>
                    </div>
                </form>
            </div>
        </div>
    </main>
</div>
<footer class="itv-login-footer"{{#if isDark}} data-dark="true"{{/if}}>{{{footer}}}</footer>
