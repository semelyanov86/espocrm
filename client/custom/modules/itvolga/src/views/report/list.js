/**
 * List of reports with the folder panel on the left (core list with categories over the flat CategoryTree
 * `ReportFolder`, D-88): opening a report shows its result; the panel gets a search by folder name and the number of
 * reports the user may read in each folder (GET Report/folderCounts). The builder is the full form (no quick create).
 */
define('itvolga:views/report/list', ['views/list-with-categories'], (ListWithCategoriesView) => {

    return class extends ListWithCategoriesView {

        categoryScope = 'ReportFolder'
        quickCreate = false

        async loadCategories() {
            await super.loadCategories();
            const view = this.getView('categories');

            if (!view) {
                return;
            }

            this.listenTo(view, 'after:render', () => this.decorateFolders(view));

            if (view.isRendered()) {
                this.decorateFolders(view);
            }
        }

        async decorateFolders(view) {
            const element = view.element;

            if (!element || element.querySelector('[data-role="folder-search"]')) {
                return;
            }

            const search = document.createElement('input');
            search.type = 'text';
            search.className = 'form-control input-sm';
            search.placeholder = this.translate('Search folders', 'labels', 'Report');
            search.dataset.role = 'folder-search';
            element.prepend(search);

            search.addEventListener('input', () => {
                const text = search.value.trim().toLowerCase();

                element.querySelectorAll('a.link[data-id]').forEach(link => {
                    const item = link.closest('li') || link.parentElement;
                    item.classList.toggle('hidden', !!text && !link.textContent.toLowerCase().includes(text));
                });
            });

            const root = element.querySelector('.root-item a.link');

            if (root) {
                root.textContent = this.translate('All Reports', 'labels', 'Report');
            }

            let counts;

            try {
                counts = await Espo.Ajax.getRequest('Report/folderCounts');
            } catch (e) {
                return;
            }

            const add = (link, n) => {
                if (link.querySelector('[data-role="count"]')) {
                    return;
                }

                const badge = document.createElement('span');
                badge.className = 'text-muted small';
                badge.dataset.role = 'count';
                badge.textContent = ' ' + n;
                link.appendChild(badge);
            };

            if (root) {
                add(root, counts.total);
            }

            element.querySelectorAll('a.link[data-id]').forEach(link => add(link, counts.folders[link.dataset.id] || 0));
        }
    };
});
