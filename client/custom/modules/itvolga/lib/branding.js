/**
 * Site footer of the company (D-127). EspoCRM has no hook for the footer view (the master and login views name
 * `views/site/footer` directly), so its template `site/footer` is registered as a pre-compiled one: the view factory
 * reads `Espo.preCompiledTemplates` when the application starts, and every footer — the application, the login page,
 * the second login step — renders this markup. Loaded after the core bundles (metadata app.client.scriptList).
 *
 * EspoCRM is AGPLv3 with a §7(b) term: its Appropriate Legal Notices keep the word "EspoCRM"; the core master view
 * puts its own footer back when the markup mentions EspoCRM fewer than twice (the link keeps three).
 */
(() => {
    const company = 'Центр информационных технологий';
    const year = new Date().getFullYear();

    const html = `<p class="credit small">&copy; ${year} ${company}. Работает на <a
        href="https://www.espocrm.com"
        title="Powered by EspoCRM"
        rel="noopener" target="_blank"
        tabindex="-1"
    >EspoCRM</a></p>`;

    window.Espo = window.Espo || {};
    Espo.preCompiledTemplates = Object.assign(Espo.preCompiledTemplates || {}, {'site/footer': () => html});
})();
