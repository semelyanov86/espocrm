/**
 * Field catalog of the report builder (GET Report/catalog/:entityType): the fields of an entity and of the entities
 * one link away that the server accepts for the current user, with what a report may do with each. Cached per
 * entity type for the page lifetime; the server checks every definition again on save and run.
 */
define('itvolga:report/catalog', [], () => {

    const cache = {};
    let entityTypes = null;

    return {
        /**
         * @return {Promise<{entityType: string, label: string}[]>}
         */
        entityTypes() {
            entityTypes = entityTypes || Espo.Ajax.getRequest('Report/catalog').then(data => data.list);

            return entityTypes;
        },

        /**
         * @param {string} entityType
         * @return {Promise<{entityType: string, fields: Object[], links: Object[], byRef: Object}>}
         */
        get(entityType) {
            if (!entityType) {
                return Promise.resolve({entityType: null, fields: [], links: [], byRef: {}});
            }

            cache[entityType] = cache[entityType] ||
                Espo.Ajax.getRequest('Report/catalog/' + encodeURIComponent(entityType)).then(data => {
                    const byRef = {};

                    data.fields.forEach(field => byRef[field.ref] = field);

                    data.links.forEach(link => {
                        link.fields.forEach(field => {
                            field.linkLabel = link.label;
                            field.linkKind = link.kind;
                            byRef[field.ref] = field;
                        });
                    });

                    data.byRef = byRef;

                    return data;
                });

            return cache[entityType];
        },

        /**
         * Label of a field reference: «Контрагент → Город» for a related field.
         *
         * @param {Object} catalog
         * @param {string} ref
         * @return {string}
         */
        label(catalog, ref) {
            const field = catalog.byRef[ref];

            if (!field) {
                return ref;
            }

            return field.linkLabel ? field.linkLabel + ' → ' + field.label : field.label;
        },

        /**
         * Grouped options for a select: main fields first, then each link.
         *
         * @param {Object} catalog
         * @param {function(Object): boolean} filter
         * @return {{label: string|null, options: {value: string, label: string}[]}[]}
         */
        groups(catalog, filter) {
            const result = [];
            const main = catalog.fields.filter(filter).map(f => ({value: f.ref, label: f.label}));

            if (main.length) {
                result.push({label: null, options: main});
            }

            catalog.links.forEach(link => {
                const options = link.fields.filter(filter).map(f => ({value: f.ref, label: link.label + ' → ' + f.label}));

                if (options.length) {
                    result.push({label: link.label, options: options});
                }
            });

            return result;
        },
    };
});
