define('itvolga:views/report/fields/columns', ['itvolga:views/report/fields/field-list'], (FieldListView) => {

    return class extends FieldListView {

        accepts(field) {
            return field.column;
        }
    };
});
