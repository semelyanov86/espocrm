/**
 * Base of the JSON parts of a report definition (columns, groups, aggregates, conditions …): the part is edited in the
 * report form as an internal state, written to the model on every change (so dependent parts — sorting by the chosen
 * columns, group sort by the chosen aggregates — follow), and checked again by the server on save (reports.md §2).
 * Options come from the field catalog of the main entity (GET Report/catalog/:entityType): the builder offers exactly
 * what the server accepts for the user.
 */
define('itvolga:views/report/fields/base', ['views/fields/base', 'itvolga:report/catalog', 'ui/select'],
    (BaseFieldView, Catalog, Select) => {

    return class extends BaseFieldView {

        listTemplateContent = ''

        /** Model attributes whose change re-renders the part. */
        dependsOn = []

        /** Value of an empty part. */
        emptyValue() {
            return [];
        }

        setup() {
            super.setup();

            this.Catalog = Catalog;
            this.catalog = {entityType: null, fields: [], links: [], byRef: {}};
            this.state = this.readState();

            this.listenTo(this.model, 'change:entityType', () => {
                this.loadCatalog().then(() => this.isRendered() && this.reRender());
            });

            this.dependsOn.forEach(attribute => {
                this.listenTo(this.model, 'change:' + attribute, () => {
                    if (this.isRendered()) {
                        // Rows dropped here are re-rendered below: until then the inputs are stale (see commit()).
                        this.domStale = true;
                        this.onDependencyChange(attribute);
                        this.reRender();
                    }
                });
            });

            this.listenTo(this.model, 'sync', () => {
                this.state = this.readState();
            });


            this.wait(this.loadCatalog());
        }

        loadCatalog() {
            return Catalog.get(this.model.get('entityType')).then(catalog => this.catalog = catalog);
        }

        /** Hook: a dependency changed (e.g. drop sorting rows of removed columns). */
        onDependencyChange() {}

        readState() {
            const value = this.model.get(this.name);

            return value === null || value === undefined ? this.emptyValue() :
                JSON.parse(JSON.stringify(value));
        }

        /**
         * Stores a changed state: the model gets it at once (dependent parts and dynamic logic follow).
         */
        commit(reRender = true) {
            // A row added or removed leaves the inputs stale until the re-render: the form calls fetch() on 'change'
            // at once, and reading the old inputs by their old indexes would overwrite the next row.
            // Only set here, cleared by afterRender: a dependency change may have set it already.
            this.domStale = this.domStale || reRender;
            this.trigger('change');

            if (reRender) {
                this.reRender();
            }
        }

        fetch() {
            return {[this.name]: JSON.parse(JSON.stringify(this.state))};
        }

        /**
         * Called by the core before a re-render caused by a change of the attribute outside the editor (save, reset).
         */
        prepare() {
            this.state = this.readState();

            return super.prepare();
        }

        afterRender() {
            super.afterRender();
            this.domStale = false;

            if (this.isEditMode() && this.element) {
                this.initSearchSelects();
            }
        }

        /** Selects of fields get a search by substring (core ui/select). */
        initSearchSelects() {
            this.element.querySelectorAll('select.itv-search:not(.selectized)')
                .forEach(element => Select.init(element, {}));
        }

        label(ref) {
            return Catalog.label(this.catalog, ref);
        }

        translateReport(label, category = 'labels') {
            return this.translate(label, category, 'Report');
        }

        /**
         * Options of a select of fields: main fields, then the fields of each link («Контрагент → Город»).
         */
        fieldOptions(filter, selected) {
            const result = [];

            Catalog.groups(this.catalog, filter).forEach(group => {
                group.options.forEach(option => result.push({
                    value: option.value,
                    label: option.label,
                    selected: option.value === selected,
                }));
            });

            return result;
        }

        moveItem(list, index, step) {
            const target = index + step;

            if (target < 0 || target >= list.length) {
                return;
            }

            [list[index], list[target]] = [list[target], list[index]];
        }
    };
});
