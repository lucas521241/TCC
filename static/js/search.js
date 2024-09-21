function initializeVue(appId) {
    new Vue({
        el: appId,
        methods: {
            submitSearch() {
                document.getElementById('search-form').submit();
            },
            handleKeyPress(event) {
                if (event.key === 'Enter') {
                    this.submitSearch();
                }
            }
        }
    });
}

initializeVue('#app-home');
initializeVue('#app-tasks');
initializeVue('#app-portal');
initializeVue('#app-config');
initializeVue('#app-search');
initializeVue('#app-users');
