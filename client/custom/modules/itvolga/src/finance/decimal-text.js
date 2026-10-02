/**
 * Decimal numbers as text (finance documents): parsing user input and formatting stored values without converting
 * them to JavaScript numbers, so no binary floating point touches money. Amounts are computed only on the server.
 */
define('itvolga:finance/decimal-text', [], () => {

    const PATTERN = /^-?\d+(\.\d+)?$/;

    return {
        /**
         * @param {*} text user input in the user's notation ("1 234,5")
         * @param {string} decimalMark
         * @param {string} thousandSeparator
         * @return {string|null} canonical decimal ("1234.5"), '' for an empty input, null if it is not a number
         */
        parse(text, decimalMark, thousandSeparator) {
            let value = String(text ?? '').replace(/[\s  ]/g, '');

            if (thousandSeparator && thousandSeparator !== decimalMark && thousandSeparator.trim() !== '') {
                value = value.split(thousandSeparator).join('');
            }

            if (decimalMark && decimalMark !== '.') {
                value = value.split(decimalMark).join('.');
            }

            if (value === '') {
                return '';
            }

            return PATTERN.test(value) ? this.canonical(value) : null;
        },

        /**
         * Without leading zeros and trailing fractional zeros: "0012.500" → "12.5".
         *
         * @param {string} value a decimal string
         * @return {string}
         */
        canonical(value) {
            const negative = value.startsWith('-');
            const [intPart, fracPart = ''] = (negative ? value.slice(1) : value).split('.');
            const int = intPart.replace(/^0+(?=\d)/, '');
            const frac = fracPart.replace(/0+$/, '');
            const result = frac ? `${int}.${frac}` : int;

            return result === '0' || !negative ? result : `-${result}`;
        },

        /**
         * @param {*} value a stored decimal string ("1500.00000000")
         * @param {{decimalMark?: string, thousandSeparator?: string, minScale?: number, grouping?: boolean}} [options]
         * @return {string} "1 500,00"; a value that is not a decimal string is returned as text
         */
        format(value, options = {}) {
            if (value === null || value === undefined || value === '') {
                return '';
            }

            const text = String(value);

            if (!PATTERN.test(text)) {
                return text;
            }

            const {decimalMark = ',', thousandSeparator = ' ', minScale = 0, grouping = true} = options;
            const canonical = this.canonical(text);
            const negative = canonical.startsWith('-');
            let [int, frac = ''] = (negative ? canonical.slice(1) : canonical).split('.');

            if (frac.length < minScale) {
                frac = frac.padEnd(minScale, '0');
            }

            if (grouping && thousandSeparator) {
                int = int.replace(/\B(?=(\d{3})+(?!\d))/g, thousandSeparator);
            }

            return (negative ? '-' : '') + int + (frac ? decimalMark + frac : '');
        },

        /**
         * @param {*} value
         * @return {boolean} empty or zero
         */
        isZero(value) {
            if (value === null || value === undefined || value === '') {
                return true;
            }

            return PATTERN.test(String(value)) && this.canonical(String(value)) === '0';
        },
    };
});
