/**
 * Main entity of a report, fixed after the first save. The offered entity types follow the server rule (D-99):
 * entity scopes that are objects or flagged `itvolgaReports: true`, `"admin"` ones for administrators only, never
 * `false` ones, readable by the user. The server checks the choice again on save and run.
 */
define('itvolga:views/report/fields/entity-type', ['views/fields/enum'], (EnumView) => {

    return class extends EnumView {

        setupOptions() {
            const scopes = this.getMetadata().get('scopes') || {};
            const isAdmin = this.getUser().isAdmin();
            const label = scope => this.translate(scope, 'scopeNamesPlural');

            const list = Object.keys(scopes).filter(scope => {
                const defs = scopes[scope] || {};
                const flag = defs.itvolgaReports;

                if (!defs.entity || defs.disabled || flag === false || (!defs.object && flag !== true && flag !== 'admin')) {
                    return false;
                }

                if (flag === 'admin' && !isAdmin) {
                    return false;
                }

                return this.getAcl().checkScope(scope, 'read');
            });

            const current = this.model.get(this.name);

            if (current && !list.includes(current)) {
                list.push(current);
            }

            list.sort((a, b) => label(a).localeCompare(label(b)));

            this.params.options = ['', ...list];
            this.params.translatedOptions = {'': ''};
            list.forEach(scope => this.params.translatedOptions[scope] = label(scope));
        }
    };
});
