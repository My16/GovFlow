document.addEventListener("DOMContentLoaded", function() {
    const forwardModal = document.getElementById("forwardModal");

    forwardModal.addEventListener("show.bs.modal", function(event) {
        const button = event.relatedTarget;
        const documentId = button.getAttribute("data-document-id");
        const form = forwardModal.querySelector("form");
        form.action = `/documents/${documentId}/forward/`;
    });
});