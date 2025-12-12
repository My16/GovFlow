function applyFilters() {
    const status = document.getElementById('statusFilter').value;
    const priority = document.getElementById('priorityFilter').value;

    const params = new URLSearchParams();
    if (status !== 'All') params.set('status', status);
    if (priority !== 'All') params.set('priority', priority);

    window.location.href = '?' + params.toString();
}

document.querySelectorAll('.view-btn').forEach(btn => {
    btn.addEventListener('click', function() {
        const url = this.getAttribute('data-url');
        const iframe = document.getElementById('pdfFrame');
        const downloadBtn = document.getElementById('pdfDownloadBtn');

        iframe.src = url;
        downloadBtn.href = url;

        const modal = new bootstrap.Modal(document.getElementById('detailsModal'));
        modal.show();
    });
});

document.addEventListener("DOMContentLoaded", function() {
    const forwardModal = document.getElementById("forwardModal");

    forwardModal.addEventListener("show.bs.modal", function(event) {
        const button = event.relatedTarget;
        const documentId = button.getAttribute("data-document-id");
        const form = forwardModal.querySelector("form");
        form.action = `/documents/${documentId}/forward/`;
    });
});