function applyFilters() {
    const status = document.getElementById('statusFilter').value;
    const priority = document.getElementById('priorityFilter').value;

    const params = new URLSearchParams();
    if (status !== 'All') params.set('status', status);
    if (priority !== 'All') params.set('priority', priority);

    window.location.href = '?' + params.toString();
}