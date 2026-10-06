<div class="itv-login"{{#if isDark}} data-dark="true"{{/if}}>
    <section class="itv-login__brand">{{{brand}}}</section>
    <main class="itv-login__side">
        <div id="login" class="itv-login__panel">
            <h1 class="itv-login__title">Вход в CRM</h1>
            <p class="itv-login__hint">Имя пользователя и пароль выдаёт администратор.</p>
            <div class="panel-body{{#if anotherUser}} another-user{{/if}}">
                <form id="login-form">
                    {{#if hasSignIn}}
                    <div class="cell" data-name="sign-in">
                        {{#if hasFallback}}
                        <div class="pull-right">
                            <a
                                role="button"
                                tabindex="0"
                                class="btn btn-link btn-icon"
                                data-action="showFallback"
                            ><span class="fas fa-chevron-down"></span></a>
                        </div>
                        {{/if}}
                        <button
                            class="btn btn-default btn-x-wide"
                            id="sign-in"
                            type="button"
                        >{{signInText}}</button>
                    </div>
                    {{/if}}
                    <div class="form-group cell" data-name="username">
                        <label for="field-userName">{{translate 'Username'}}</label>
                        <input
                            type="text"
                            name="username"
                            id="field-userName"
                            class="form-control"
                            autocapitalize="off"
                            spellcheck="false"
                            tabindex="1"
                            autocomplete="username"
                            maxlength="255"
                        >
                    </div>
                    <div class="form-group cell" data-name="password">
                        <label for="field-password">{{translate 'Password'}}</label>
                        <div data-role="password-input-container">
                            <input
                                type="password"
                                name="password"
                                id="field-password"
                                class="form-control"
                                tabindex="2"
                                autocomplete="current-password"
                                maxlength="255"
                            >
                            <a
                                role="button"
                                data-action="toggleShowPassword"
                                class="text-soft"
                                title="{{translate 'View'}}"
                            ><span class="far fa-eye"></span></a>
                        </div>
                    </div>
                    {{#if anotherUser}}
                    <div class="form-group cell">
                        <label>{{translate 'Log in as'}}</label>
                        <div>{{anotherUser}}</div>
                    </div>
                    {{/if}}
                    <div class="cell itv-login__actions" data-name="submit">
                        <button
                            type="submit"
                            class="btn btn-primary itv-login__submit"
                            id="btn-login"
                            tabindex="3"
                        >{{logInText}}</button>
                        {{#if showForgotPassword}}
                        <a
                            role="button"
                            class="btn btn-link btn-text btn-text-hoverable btn-sm"
                            data-action="passwordChangeRequest"
                            tabindex="4"
                        >{{translate 'Forgot Password?' scope='User'}}</a>{{/if}}
                    </div>
                </form>
            </div>
        </div>
    </main>
</div>
<footer class="itv-login-footer"{{#if isDark}} data-dark="true"{{/if}}>{{{footer}}}</footer>
