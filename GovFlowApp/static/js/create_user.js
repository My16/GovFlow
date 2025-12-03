// Wait for the DOM to fully load
document.addEventListener("DOMContentLoaded", function() {
    // Select all alert messages
    const alerts = document.querySelectorAll(".alert");

    alerts.forEach((alert) => {
        // Set timeout to hide the alert after 3 seconds (3000ms)
        setTimeout(() => {
            alert.style.transition = "opacity 0.5s, transform 0.5s";
            alert.style.opacity = "0";
            alert.style.transform = "translateY(-10px)";
            // Remove the element after the transition
            setTimeout(() => alert.remove(), 500);
        }, 3000);
    });
});

// Password visibility toggle
document.addEventListener("DOMContentLoaded", function() {
    const toggles = document.querySelectorAll(".toggle-password");

    toggles.forEach(toggle => {
        toggle.addEventListener("click", function() {
            const targetId = this.dataset.target;
            const input = document.getElementById(targetId);

            if (input.type === "password") {
                input.type = "text";
                this.classList.remove("bi-eye");
                this.classList.add("bi-eye-slash");
            } else {
                input.type = "password";
                this.classList.remove("bi-eye-slash");
                this.classList.add("bi-eye");
            }
        });
    });
});
