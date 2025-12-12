document.addEventListener("DOMContentLoaded", function () {

    // --- Sidebar and Header Toggle ---
    const sidebar = document.getElementById('sidebar');
    const mainContent = document.getElementById('mainContent');
    const headerToggleBtn = document.getElementById('headerToggle'); 
    const desktopToggleBtn = document.getElementById('desktopToggle'); 
    const mediaQueryLarge = window.matchMedia('(min-width: 992px)');

    const toggleSidebar = () => {
        const isDesktop = mediaQueryLarge.matches;

        if (isDesktop) {
            sidebar.classList.toggle('collapsed');
            mainContent.classList.toggle('sidebar-collapsed-active');
            
            const arrowIcon = desktopToggleBtn.querySelector('i');
            if (sidebar.classList.contains('collapsed')) {
                arrowIcon.classList.remove('bi-chevron-left');
                arrowIcon.classList.add('bi-chevron-right');
                headerToggleBtn.style.display = 'flex'; 
            } else {
                arrowIcon.classList.remove('bi-chevron-right');
                arrowIcon.classList.add('bi-chevron-left');
                headerToggleBtn.style.display = 'none'; 
            }

        } else {
            sidebar.classList.toggle('active');
        }
    };

    // Initial state
    if (mediaQueryLarge.matches) {
        sidebar.classList.remove('collapsed');
        mainContent.classList.remove('sidebar-collapsed-active');
        const arrowIcon = desktopToggleBtn.querySelector('i');
        arrowIcon.classList.remove('bi-chevron-right');
        arrowIcon.classList.add('bi-chevron-left');
        headerToggleBtn.style.display = 'none'; 
    }

    desktopToggleBtn.addEventListener('click', toggleSidebar);
    headerToggleBtn.addEventListener('click', (e) => {
        e.stopPropagation(); 
        toggleSidebar();
    });

    mainContent.addEventListener('click', () => {
        if (!mediaQueryLarge.matches && sidebar.classList.contains('active')) {
            sidebar.classList.remove('active');
        }
    });

    mediaQueryLarge.addEventListener('change', function(mq) {
        if (mq.matches) {
            sidebar.classList.remove('collapsed');
            mainContent.classList.remove('sidebar-collapsed-active');
            desktopToggleBtn.querySelector('i').classList.remove('bi-chevron-right');
            desktopToggleBtn.querySelector('i').classList.add('bi-chevron-left');
            sidebar.classList.remove('active');
            desktopToggleBtn.style.display = 'flex'; 
            headerToggleBtn.style.display = 'none'; 
        } else {
            sidebar.classList.remove('collapsed');
            mainContent.classList.remove('sidebar-collapsed-active');
            sidebar.classList.remove('active');
            desktopToggleBtn.style.display = 'none';
            headerToggleBtn.style.display = 'flex'; 
        }
    });

    if (!mediaQueryLarge.matches) {
        desktopToggleBtn.style.display = 'none';
        headerToggleBtn.style.display = 'flex';
    } else {
        desktopToggleBtn.style.display = 'flex';
    }

    // --- Profile Dropdown ---
    const profileAvatar = document.querySelector('.profile-avatar');
    const profileDropdown = document.querySelector('.profile-dropdown');

    profileAvatar.addEventListener('click', function(e) {
        e.stopPropagation();
        profileDropdown.style.display = (profileDropdown.style.display === 'flex') ? 'none' : 'flex';
    });

    document.addEventListener('click', function() {
        profileDropdown.style.display = 'none';
    });

    // --- Toast Notifications ---
    const toastElList = document.querySelectorAll('.toast');
    toastElList.forEach(function(toastEl) {
        const toast = new bootstrap.Toast(toastEl, { delay: 3000 });
        toast.show();
    });

    // --- QR Scanner Modal ---
    const receiveModal = document.getElementById("receiveModal");
    let html5QrcodeScanner;

    if (receiveModal) {
        receiveModal.addEventListener("shown.bs.modal", function () {
            if (!html5QrcodeScanner) {
                html5QrcodeScanner = new Html5Qrcode("qr-scanner");
            }

            Html5Qrcode.getCameras().then(cameras => {
                if (cameras && cameras.length) {
                    const cameraId = cameras[0].id;
                    html5QrcodeScanner.start(
                        cameraId,
                        { fps: 10, qrbox: 250 },
                        qrCodeMessage => {
                            console.log("QR Scanned:", qrCodeMessage);
                            const manualInput = document.getElementById("manualTracking");
                            if (manualInput) {
                                manualInput.value = qrCodeMessage.toUpperCase();
                                // Auto-submit the form
                                if (manualInput.form) {
                                    manualInput.form.submit();
                                }
                            }
                        },
                        errorMessage => { /* optional: ignore */ }
                    ).catch(err => console.error("QR Start Error:", err));
                } else {
                    console.warn("No cameras found");
                }
            }).catch(err => console.error("Camera Error:", err));
        });

        receiveModal.addEventListener("hidden.bs.modal", function () {
            if (html5QrcodeScanner) {
                html5QrcodeScanner.stop().then(() => html5QrcodeScanner.clear())
                .catch(err => console.error("QR Stop Error:", err));
            }
        });
    }

});
