    <script>
        const ARTICLES_I18N = @json($articlesI18n);
        const TRASH_I18N = @json($trashI18n);
        const IS_TRASH_VIEW = @json($isTrashView);
        const EMPTY_TRASH_URL = @json(route('admin.articles.trash.empty', [], false));

        function toggleBatchActions() {
            const batchActions = document.getElementById('batch-actions');
            const checkboxes = document.querySelectorAll('.batch-checkbox');
            if (!batchActions) {
                return;
            }

            const isHidden = batchActions.classList.contains('hidden');
            if (isHidden) {
                batchActions.classList.remove('hidden');
                checkboxes.forEach((node) => node.classList.remove('hidden'));
                return;
            }

            batchActions.classList.add('hidden');
            checkboxes.forEach((node) => node.classList.add('hidden'));
            document.querySelectorAll('.article-checkbox').forEach((node) => node.checked = false);
            const selectAll = document.getElementById('select-all');
            if (selectAll) {
                selectAll.checked = false;
            }
            updateSelectedCount();
        }

        function updateSelectedCount() {
            const countElement = document.getElementById('selected-count');
            if (!countElement) {
                return;
            }
            countElement.textContent = String(document.querySelectorAll('.article-checkbox:checked').length);
        }

        const ARTICLE_BATCH_ROUTES = @json($articleBatchRoutes);

        function submitEmptyTrash() {
            if (!confirm(TRASH_I18N.confirmEmpty)) {
                return;
            }
            const form = document.createElement('form');
            form.method = 'POST';
            form.action = EMPTY_TRASH_URL;
            form.style.display = 'none';
            form.innerHTML = `<input type="hidden" name="_token" value="{{ csrf_token() }}">`;
            document.body.appendChild(form);
            form.submit();
        }

        function submitAction(action, articleId, extra = {}) {
            const targetAction = ARTICLE_BATCH_ROUTES[action] ?? '';
            if (targetAction === '') {
                return;
            }

            const form = document.createElement('form');
            form.method = 'POST';
            form.action = targetAction;
            form.style.display = 'none';
            form.innerHTML = `
                <input type="hidden" name="_token" value="{{ csrf_token() }}">
                <input type="hidden" name="article_ids[]" value="${articleId}">
            `;
            Object.entries(extra).forEach(([key, value]) => {
                const input = document.createElement('input');
                input.type = 'hidden';
                input.name = key;
                input.value = String(value);
                form.appendChild(input);
            });
            document.body.appendChild(form);
            form.submit();
        }

        function deleteArticle(articleId) {
            if (!confirm(ARTICLES_I18N.confirmDelete)) {
                return;
            }
            submitAction('delete_articles', articleId);
        }

        function quickReview(articleId, status) {
            const actionText = status === 'approved' ? ARTICLES_I18N.reviewApproved : ARTICLES_I18N.reviewRejected;
            if (!confirm(ARTICLES_I18N.confirmQuickReview.replace('__ACTION__', actionText))) {
                return;
            }
            submitAction('batch_update_review', articleId, { review_status: status });
        }

        document.addEventListener('DOMContentLoaded', function() {
            const selectAll = document.getElementById('select-all');
            if (selectAll) {
                selectAll.addEventListener('change', function() {
                    document.querySelectorAll('.article-checkbox').forEach((node) => node.checked = this.checked);
                    updateSelectedCount();
                });
            }

            document.querySelectorAll('.article-checkbox').forEach((node) => {
                node.addEventListener('change', updateSelectedCount);
            });

            const batchAction = document.getElementById('batch-action');
            if (batchAction && !IS_TRASH_VIEW) {
                batchAction.addEventListener('change', function() {
                    const statusSelect = document.getElementById('status-select');
                    const reviewSelect = document.getElementById('review-select');
                    statusSelect?.classList.add('hidden');
                    reviewSelect?.classList.add('hidden');
                    if (this.value === 'batch_update_status') {
                        statusSelect?.classList.remove('hidden');
                    } else if (this.value === 'batch_update_review') {
                        reviewSelect?.classList.remove('hidden');
                    }
                });
            }

            const batchForm = document.getElementById('batch-form');
            if (batchForm) {
                batchForm.addEventListener('submit', function(event) {
                    const selected = document.querySelectorAll('.article-checkbox:checked');
                    if (selected.length === 0) {
                        event.preventDefault();
                        alert(IS_TRASH_VIEW ? TRASH_I18N.alertSelect : ARTICLES_I18N.selectArticles);
                        return;
                    }

                    const action = document.getElementById('batch-action')?.value ?? '';
                    if (action === '') {
                        event.preventDefault();
                        alert(ARTICLES_I18N.selectAction);
                        return;
                    }

                    const targetAction = ARTICLE_BATCH_ROUTES[action] ?? '';
                    if (targetAction === '') {
                        event.preventDefault();
                        alert(ARTICLES_I18N.selectAction);
                        return;
                    }
                    batchForm.action = targetAction;

                    if (IS_TRASH_VIEW) {
                        if (action === 'batch_restore' && !confirm(TRASH_I18N.confirmBatchRestore.replace('__COUNT__', String(selected.length)))) {
                            event.preventDefault();
                            return;
                        }
                        if (action === 'batch_force_delete' && !confirm(TRASH_I18N.confirmBatchForceDelete.replace('__COUNT__', String(selected.length)))) {
                            event.preventDefault();
                            return;
                        }
                    } else {
                    if (action === 'batch_update_status' && !(document.getElementById('status-select')?.value ?? '')) {
                        event.preventDefault();
                        alert(ARTICLES_I18N.selectStatus);
                        return;
                    }

                    if (action === 'batch_update_review' && !(document.getElementById('review-select')?.value ?? '')) {
                        event.preventDefault();
                        alert(ARTICLES_I18N.selectReview);
                        return;
                    }

                    if (action === 'delete_articles' && !confirm(ARTICLES_I18N.confirmDeleteSelected.replace('__COUNT__', selected.length))) {
                        event.preventDefault();
                        return;
                    }
                    }

                    const selectedIdsContainer = document.getElementById('batch-selected-ids');
                    if (!selectedIdsContainer) {
                        return;
                    }
                    selectedIdsContainer.innerHTML = '';
                    selected.forEach((checkbox) => {
                        const input = document.createElement('input');
                        input.type = 'hidden';
                        input.name = 'article_ids[]';
                        input.value = checkbox.value;
                        selectedIdsContainer.appendChild(input);
                    });
                });
            }
        });
    </script>
