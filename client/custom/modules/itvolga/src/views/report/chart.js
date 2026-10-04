/**
 * One chart of a report (D-105…D-108), drawn from the chart data of the run with the libraries of the core only:
 * Flotr2 (bars, stacked and horizontal bars, line, pie, two rings) and EspoFunnel. Points are the table's cells: `v`
 * becomes a float here only to be plotted, labels and tooltips show the server's `f`. Colors come from the theme as in
 * the core chart dashlets. A click on a bar, point, slice or funnel step triggers `drill-down` with the group path.
 * Text is drawn on the canvas or escaped; nothing of the data is inserted as HTML.
 */
define('itvolga:views/report/chart', ['view', 'lib!flotr2', 'lib!espo-funnel-chart'], (View, Flotr) => {

    const DEFAULT_COLORS = ['#6FA8D6', '#4E6CAD', '#EDC555', '#ED8F42', '#DE6666', '#7CC4A4', '#8A7CC2', '#D4729B'];
    const BAR_TYPES = ['bar', 'stackedBar', 'horizontalBar', 'stackedHorizontalBar', 'line'];
    // Room for the labels Flotr2 draws outside a pie.
    const PIE_RATIO = 0.6;
    const INNER_RATIO = 0.45;
    const OUTER_RATIO = 0.75;

    return class extends View {

        templateContent = `
            <div class="chart-container" data-role="chart"></div>
            <div class="legend-container small" data-role="legend"></div>`

        setup() {
            this.chart = this.options.chart;
            this.item = this.chart.items[this.options.index];
            this.height = this.options.height || 300;
            this.drillPaths = {};

            const theme = this.getThemeManager();
            this.colors = theme.getParam('chartColorList') || DEFAULT_COLORS;
            this.gridColor = theme.getParam('chartGridColor') || '#ddd';
            this.tickColor = theme.getParam('chartTickColor') || '#e8eced';
            this.textColor = theme.getParam('textColor') || '#333';
            this.hoverColor = theme.getParam('hoverColor') || '#FF3F19';

            this.on('resize', () => this.isRendered() && this.draw());
            $(window).on('resize.itvReportChart' + this.cid, () => this.isRendered() && this.draw());
            this.once('remove', () => {
                $(window).off('resize.itvReportChart' + this.cid);
                this.destroyGraphs();
            });
        }

        afterRender() {
            this.box = this.element.querySelector('[data-role="chart"]');
            this.legend = this.element.querySelector('[data-role="legend"]');
            this.box.style.height = this.height + 'px';
            // The pointer as the rings need it for tooltips: caught before Flotr2 handles the move (it updates its own
            // last position only after the tooltip).
            this.box.addEventListener('mousemove', e => {
                this.pointer = {x: e.clientX, y: e.clientY};
                // After Flotr2 has handled the move (the rings correct its tooltip).
                requestAnimationFrame(() => this.afterPointer && this.afterPointer());
            }, true);
            this.element.dataset.chartType = this.item.type;
            this.element.dataset.categories = String(this.chart.categories.length);
            this.element.dataset.series = String(this.item.series.length);
            this.draw();
        }

        /** Escaped text for the places where Flotr takes HTML (legend, tooltip). */
        esc(text) {
            return this.getHelper().escapeString(text === null || text === undefined ? '' : String(text));
        }

        /** The value a chart draws: none for an empty or mixed-currency cell. */
        num(point) {
            if (!point || point.v === null || point.v === undefined || point.mixed) {
                return null;
            }

            const value = parseFloat(point.v);

            return isNaN(value) ? null : value;
        }

        tick(value) {
            const number = parseFloat(value);
            const abs = Math.abs(number);
            const util = this.getNumberUtil();

            if (abs >= 1000000) {
                return util.formatFloat(Math.round(number / 10000) / 100) + 'M';
            }

            if (abs >= 10000) {
                return util.formatFloat(Math.round(number / 10) / 100) + 'k';
            }

            return util.formatFloat(Math.round(number * 100) / 100);
        }

        message(text) {
            this.box.innerHTML = '';
            this.legend.innerHTML = '';
            const span = document.createElement('span');
            span.className = 'text-muted';
            span.textContent = text;
            this.box.appendChild(span);
        }

        draw() {
            if (!this.box || !this.box.offsetWidth) {
                // Hidden (a collapsed panel, a background tab): drawn on the next resize.
                return;
            }

            this.destroyGraphs();
            this.box.innerHTML = '';
            this.legend.innerHTML = '';

            if (this.item.unavailable) {
                this.message(this.translate('chartMixedCurrencies', 'labels', 'Report'));

                return;
            }

            if (!this.chart.categories.length) {
                this.message(this.translate('No data', 'labels', 'Report'));

                return;
            }

            if (BAR_TYPES.includes(this.item.type)) {
                this.drawBars();
            } else if (this.item.type === 'funnel') {
                this.drawFunnel();
            } else if (this.item.inner) {
                this.drawRings();
            } else {
                this.drawPie();
            }
        }

        /** Graphs of the last draw with their handlers (observed through the graph, so destroy() removes them). */
        destroyGraphs() {
            (this.graphs || []).forEach(graph => graph.destroy());
            this.graphs = [];
            this.afterPointer = null;
        }

        /** A click on the graph opens the records of the group under the mouse. */
        observeClick(graph, resolve) {
            this.graphs.push(graph);
            graph.observe(this.box, 'flotr:click', (position, current) => {
                const path = resolve(position, current);

                if (path) {
                    this.trigger('drill-down', path);
                }
            });
        }

        legendOptions(columns) {
            return {
                show: true,
                container: this.legend,
                noColumns: columns || Math.max(1, Math.floor(this.box.offsetWidth / 140)),
                labelBoxBorderColor: 'transparent',
                backgroundOpacity: 0,
                // Labels are escaped where the series are made; the color is the theme's text color.
                labelFormatter: label => `<span style="color: ${this.textColor}">${label}</span>`,
            };
        }

        drawBars() {
            const item = this.item;
            const type = item.type;
            const horizontal = type === 'horizontalBar' || type === 'stackedHorizontalBar';
            const stacked = type === 'stackedBar' || type === 'stackedHorizontalBar';
            const line = type === 'line';
            const categories = this.chart.categories;
            const n = categories.length;
            // Horizontal bars list the first category on top.
            const at = i => horizontal ? n - 1 - i : i;
            const point = (i, value) => horizontal ? [value, at(i)] : [at(i), value];
            // Flotr2 bars cannot hit-test an empty point: a missing pair is a bar of zero; a line keeps its gap.
            const value = p => this.num(p) ?? (line ? null : 0);
            const data = item.series.map((series, s) => ({
                label: this.esc(series.label),
                data: series.points.map((p, i) => point(i, value(p))),
                itvSeries: s,
                color: this.colors[s % this.colors.length],
            }));
            const progress = item.progress || {};

            Object.keys(progress).forEach((fn, k) => data.push({
                label: this.esc(this.getLanguage().translateOption(fn, 'progressLine', 'Report')),
                data: progress[fn].map((cell, i) => point(i, this.num(cell))),
                itvProgress: fn,
                color: this.colors[(item.series.length + k) % this.colors.length],
                lines: {show: true, lineWidth: 1},
                points: {show: true, radius: 2},
                bars: {show: false},
            }));

            const values = data.flatMap(series => series.data.map(p => horizontal ? p[0] : p[1]))
                .filter(v => v !== null);

            // The highest and the lowest bar (of a stack: the sums of its positive and of its negative parts) or point
            // get some room; both bounds are set, as Flotr2 extends the range of stacks only when none is.
            if (stacked) {
                categories.forEach((c, i) => values.push(
                    item.series.reduce((sum, series) => sum + Math.max(0, this.num(series.points[i]) ?? 0), 0),
                    item.series.reduce((sum, series) => sum + Math.min(0, this.num(series.points[i]) ?? 0), 0)));
            }

            const top = Math.max(0, ...values);
            const bottom = Math.min(0, ...values);
            const categoryAxis = {
                ticks: categories.map((c, i) => [at(i), c.key.f]),
                min: -0.5,
                max: n - 0.5,
                labelsAngle: !horizontal && n > 6 ? 45 : 0,
                color: this.textColor,
            };
            const valueAxis = {
                min: bottom < 0 ? bottom * 1.08 : 0,
                max: top > 0 ? top * 1.08 : (bottom < 0 ? 0 : null),
                tickFormatter: v => this.tick(v),
                color: this.textColor,
            };

            const graph = Flotr.draw(this.box, data, {
                colors: this.colors,
                shadowSize: false,
                HtmlText: false,
                bars: {show: !line, horizontal: horizontal, stacked: stacked,
                    grouped: !stacked && !line && item.series.length > 1, barWidth: 0.6, lineWidth: 1,
                    fillOpacity: 1, shadowSize: 0},
                lines: {show: line, lineWidth: 2},
                points: {show: line, radius: 3},
                grid: {horizontalLines: !horizontal, verticalLines: horizontal, outline: 'sw', color: this.gridColor,
                    tickColor: this.tickColor},
                xaxis: horizontal ? valueAxis : categoryAxis,
                yaxis: horizontal ? categoryAxis : valueAxis,
                mouse: {track: true, relative: true, lineColor: this.hoverColor, position: horizontal ? 'w' : 'n',
                    trackFormatter: obj => this.barTooltip(obj, horizontal, n)},
                legend: data.length > 1 ? this.legendOptions() : {show: false},
            });

            this.observeClick(graph, position => {
                const hit = position.hit;

                if (!hit || hit.series === undefined || hit.series.itvSeries === undefined) {
                    return null;
                }

                const p = item.series[hit.series.itvSeries].points[hit.index];

                return p ? p.path : null;
            });
        }

        barTooltip(obj, horizontal, n) {
            const series = obj.series || {};
            const index = obj.index;
            const category = this.chart.categories[index];
            let cell = null;
            let label = '';

            if (series.itvProgress) {
                cell = (this.item.progress[series.itvProgress] || [])[index];
                label = this.getLanguage().translateOption(series.itvProgress, 'progressLine', 'Report');
            } else if (series.itvSeries !== undefined) {
                cell = this.item.series[series.itvSeries].points[index];
                label = this.item.series[series.itvSeries].label;
            }

            return (category ? this.esc(category.key.f) + '<br>' : '') + this.esc(label) + ': ' +
                '<span class="numeric-text">' + this.esc(cell ? cell.f : '') + '</span>';
        }

        /** Slices of a pie: the drawn (positive) points with the category or pair they show. */
        slices(points, labelOf) {
            const list = [];

            points.forEach((p, i) => {
                const value = this.num(p);

                if (value !== null && value > 0) {
                    list.push({point: p, value: value, label: labelOf(i)});
                }
            });

            return list;
        }

        pieLabel(slice) {
            if (this.item.type === 'piePercent') {
                return slice.point.share ? slice.point.share.f : '';
            }

            return slice.point.f;
        }

        drawPie() {
            const points = this.item.series[0].points;
            const slices = this.slices(points, i => this.chart.categories[i].key.f);
            const total = slices.reduce((sum, s) => sum + s.value, 0);

            if (!slices.length) {
                this.message(this.translate('No data', 'labels', 'Report'));

                return;
            }

            const graph = Flotr.draw(this.box, slices.map((s, i) => ({
                label: this.esc(s.label),
                data: [[0, s.value]],
                color: this.colors[i % this.colors.length],
            })), {
                shadowSize: false,
                HtmlText: false,
                pie: {show: true, explode: 0, lineWidth: 1, fillOpacity: 1, sizeRatio: PIE_RATIO,
                    labelFormatter: (sum, value) => {
                        const slice = slices.find(s => s.value === value);

                        return 100 * value / total < 5 || !slice ? '' : this.pieLabel(slice);
                    }},
                grid: {horizontalLines: false, verticalLines: false, outline: ''},
                xaxis: {showLabels: false},
                yaxis: {showLabels: false},
                mouse: {track: true, relative: true, lineColor: this.hoverColor,
                    trackFormatter: obj => this.sliceTooltip(slices[obj.nearest.seriesIndex])},
                legend: this.legendOptions(),
            });

            this.observeClick(graph, position => position.hit && slices[position.hit.seriesIndex] ?
                slices[position.hit.seriesIndex].point.path : null);
        }

        sliceTooltip(slice) {
            if (!slice) {
                return '';
            }

            return this.esc(slice.label) + '<br><span class="numeric-text">' + this.esc(slice.point.f) +
                (slice.point.share ? ' / ' + this.esc(slice.point.share.f) : '') + '</span>';
        }

        /**
         * Two rings (axis «group 1 → group 2», D-108): the inner disk shows group 1, the outer ring the pairs of
         * groups 1 and 2 in the order of the categories. Two Flotr2 pies of one size share the center: the outer one
         * below, the inner one above it (its canvas lets the mouse through); which ring is under the mouse is told by
         * the distance from the center.
         */
        drawRings() {
            const categories = this.chart.categories;
            const inner = this.slices(this.item.inner, i => categories[i].key.f);
            const outerPoints = [];

            categories.forEach((c, i) => this.item.series.forEach(series => outerPoints.push({
                point: series.points[i], label: c.key.f + ' → ' + series.label, color: series})));

            const outer = this.slices(outerPoints.map(o => o.point), k => outerPoints[k].label);

            if (!inner.length || !outer.length) {
                this.message(this.translate('No data', 'labels', 'Report'));

                return;
            }

            const seriesColor = series => this.colors[this.item.series.indexOf(series) % this.colors.length];
            const outerColors = outer.map(s => seriesColor(outerPoints.find(o => o.point === s.point).color));
            const innerColors = inner.map((s, i) => this.colors[(this.item.series.length + i) % this.colors.length]);

            this.box.style.position = 'relative';
            const top = document.createElement('div');
            top.style.position = 'absolute';
            top.style.left = '0';
            top.style.top = '0';
            top.style.width = this.box.offsetWidth + 'px';
            top.style.height = this.box.offsetHeight + 'px';
            top.style.pointerEvents = 'none';

            const options = (slices, ratio, labels) => ({
                shadowSize: false,
                HtmlText: false,
                pie: {show: true, explode: 0, lineWidth: 1, fillOpacity: 1, sizeRatio: ratio, startAngle: 0,
                    labelFormatter: (sum, value) => {
                        const slice = slices.find(s => s.value === value);

                        return !labels || !slice || 100 * value / sum < 5 ? '' : this.pieLabel(slice);
                    }},
                grid: {horizontalLines: false, verticalLines: false, outline: ''},
                xaxis: {showLabels: false},
                yaxis: {showLabels: false},
                legend: {show: false},
            });
            let outerIndex = null;
            const outerGraph = Flotr.draw(this.box, outer.map((s, i) => ({data: [[0, s.value]], color: outerColors[i]})),
                {...options(outer, OUTER_RATIO, false), mouse: {track: true, relative: true, lineColor: this.hoverColor,
                    trackFormatter: obj => {
                        outerIndex = obj.nearest.seriesIndex;

                        return this.sliceTooltip(this.ringAt(outerGraph, inner, outer, outerIndex));
                    }}});

            this.box.appendChild(top);
            this.graphs.push(Flotr.draw(top, inner.map((s, i) => ({data: [[0, s.value]], color: innerColors[i]})),
                options(inner, INNER_RATIO, true)));
            this.ringsLegend(inner, innerColors);

            // Flotr2 redraws its tooltip only when the slice of the outer pie changes, but that pie lies under the
            // inner disk too: the text follows the ring under the mouse.
            this.afterPointer = () => {
                const tip = this.box.querySelector('.flotr-mouse-value');

                if (tip && tip.style.display !== 'none') {
                    tip.innerHTML = this.sliceTooltip(this.ringAt(outerGraph, inner, outer, outerIndex));
                }
            };

            this.observeClick(outerGraph, (position, graph) => {
                const slice = this.ringAt(graph, inner, outer, position.hit ? position.hit.seriesIndex : null,
                    position);

                return slice ? slice.point.path : null;
            });
        }

        /**
         * The slice under the mouse: of the inner disk when nearer to the center than its radius (by the angle as
         * Flotr2 lays the slices out from startAngle 0), else the outer slice Flotr2 found.
         */
        ringAt(graph, inner, outer, outerIndex, position) {
            let pos = position;

            if (!pos && this.pointer && graph.plotOffset) {
                const rect = this.box.getBoundingClientRect();
                pos = {relX: this.pointer.x - rect.left - graph.plotOffset.left,
                    relY: this.pointer.y - rect.top - graph.plotOffset.top};
            }

            if (pos && graph.plotWidth) {
                const dx = pos.relX - graph.plotWidth / 2;
                const dy = pos.relY - graph.plotHeight / 2;
                const radius = Math.min(graph.plotWidth, graph.plotHeight) * INNER_RATIO / 2;

                if (Math.sqrt(dx * dx + dy * dy) <= radius) {
                    const total = inner.reduce((sum, s) => sum + s.value, 0);
                    let angle = Math.atan2(dy, dx);
                    angle = angle < 0 ? angle + 2 * Math.PI : angle;
                    let start = 0;

                    for (const slice of inner) {
                        const end = start + 2 * Math.PI * slice.value / total;

                        if (angle >= start && angle < end) {
                            return slice;
                        }

                        start = end;
                    }

                    return null;
                }
            }

            return outerIndex === null || outerIndex === undefined ? null : outer[outerIndex] || null;
        }

        /**
         * A legend of colored entries (rings and funnel; the bars and the pie use the legend of Flotr2).
         *
         * @param {{label: string, color: string}[][]} lines
         */
        drawLegend(lines) {
            lines.forEach((entries, i) => {
                if (i > 0) {
                    this.legend.appendChild(document.createElement('br'));
                }

                entries.forEach(entry => {
                    const box = document.createElement('span');
                    box.className = 'fas fa-square';
                    box.style.color = entry.color;
                    this.legend.append(box, document.createTextNode(' ' + entry.label + '\u2003'));
                });
            });
        }

        /** Legend of the rings: categories (inner disk), then the series of group 2 (outer ring). */
        ringsLegend(inner, innerColors) {
            this.drawLegend([
                inner.map((s, i) => ({label: s.label, color: innerColors[i]})),
                this.item.series.map((series, s) => ({label: series.label, color: this.colors[s % this.colors.length]})),
            ]);
        }

        drawFunnel() {
            const categories = this.chart.categories;
            const steps = this.slices(this.item.series[0].points, i => categories[i].key.f);

            if (!steps.length) {
                this.message(this.translate('No data', 'labels', 'Report'));

                return;
            }

            const colors = steps.map((s, i) => this.colors[i % this.colors.length]);

            new window.EspoFunnel.Funnel(this.box, {
                colors: colors,
                outlineColor: this.hoverColor,
                callbacks: {
                    tooltipHtml: i => this.sliceTooltip(steps[i]),
                },
                events: {
                    leftClick: ({index}) => steps[index] && this.trigger('drill-down', steps[index].point.path),
                },
                tooltipClassName: 'flotr-mouse-value',
                tooltipStyleString: 'opacity:0.7;background-color:#000;color:#fff;position:absolute;' +
                    'padding:2px 8px;border-radius:4px;white-space:nowrap;',
            }, steps.map(s => ({value: s.value})));

            this.drawLegend([steps.map((s, i) => ({label: s.label, color: colors[i]}))]);
        }
    };
});
