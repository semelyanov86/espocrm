/**
 * Money of finance documents (decimal currency fields): shown from the stored decimal string. The core view rounds
 * through Math.round(value × 10ⁿ) — binary floating point — before display; editing stays the core one, which
 * already sends decimal fields as strings.
 */
define('itvolga:views/fields/money', ['views/fields/currency', 'itvolga:finance/decimal-text'],
    (CurrencyFieldView, DecimalText) => {

    return class extends CurrencyFieldView {

        formatNumberDetail(value) {
            if (value === null || value === undefined || value === '') {
                return '';
            }

            return DecimalText.format(String(value), {
                decimalMark: this.decimalMark,
                thousandSeparator: this.thousandSeparator,
                minScale: 2,
            });
        }
    };
});
