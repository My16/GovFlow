const sidebar = document.getElementById('sidebar');
    const mainContent = document.getElementById('mainContent');
    const headerToggleBtn = document.getElementById('headerToggle'); 
    const desktopToggleBtn = document.getElementById('desktopToggle'); 
    const mediaQueryLarge = window.matchMedia('(min-width: 992px)');


    // --- Core Toggle Function (used by both buttons) ---
    const toggleSidebar = () => {
        const isDesktop = mediaQueryLarge.matches;

        if (isDesktop) {
            // Desktop collapse/expand
            sidebar.classList.toggle('collapsed');
            mainContent.classList.toggle('sidebar-collapsed-active');
            
            // Toggle arrow direction
            const arrowIcon = desktopToggleBtn.querySelector('i');
            if (sidebar.classList.contains('collapsed')) {
                arrowIcon.classList.remove('bi-chevron-left');
                arrowIcon.classList.add('bi-chevron-right');
                // Show header button when collapsed
                headerToggleBtn.style.display = 'flex'; 
            } else {
                arrowIcon.classList.remove('bi-chevron-right');
                arrowIcon.classList.add('bi-chevron-left');
                // Hide header button when open
                headerToggleBtn.style.display = 'none'; 
            }

        } else {
            // Mobile slide in/out
            sidebar.classList.toggle('active');
        }
    };
    
    // --- Initialization and Event Listeners ---

    // Set initial state: Open on desktop, hidden on mobile.
    if (mediaQueryLarge.matches) {
        // Ensure the sidebar is OPEN on load 
        sidebar.classList.remove('collapsed');
        mainContent.classList.remove('sidebar-collapsed-active');
        
        // Ensure the arrow points left (ready to collapse) and header button is hidden
        const arrowIcon = desktopToggleBtn.querySelector('i');
        arrowIcon.classList.remove('bi-chevron-right');
        arrowIcon.classList.add('bi-chevron-left');
        headerToggleBtn.style.display = 'none'; 
    }


    // 1. Desktop Collapse Button Listener (at bottom of sidebar)
    desktopToggleBtn.addEventListener('click', toggleSidebar);
    
    // 2. Header Toggle Button Listener (for mobile and collapsed desktop)
    headerToggleBtn.addEventListener('click', (e) => {
        e.stopPropagation(); 
        toggleSidebar();
    });

    // 3. Close sidebar on click outside when on mobile (good UX)
    mainContent.addEventListener('click', () => {
        if (!mediaQueryLarge.matches && sidebar.classList.contains('active')) {
            sidebar.classList.remove('active');
        }
    });

    // 4. Reset sidebar classes when screen size changes
    mediaQueryLarge.addEventListener('change', function(mq) {
        if (mq.matches) {
            // If switching to desktop, ensure the sidebar is OPEN and reset mobile classes
            sidebar.classList.remove('collapsed');
            mainContent.classList.remove('sidebar-collapsed-active');
            desktopToggleBtn.querySelector('i').classList.remove('bi-chevron-right');
            desktopToggleBtn.querySelector('i').classList.add('bi-chevron-left');
            sidebar.classList.remove('active');
            
            // Ensure the desktop collapse button is visible, hide header button
            desktopToggleBtn.style.display = 'flex'; 
            headerToggleBtn.style.display = 'none'; 
        } else {
            // If switching to mobile, ensure desktop classes are gone and set mobile buttons
            sidebar.classList.remove('collapsed');
            mainContent.classList.remove('sidebar-collapsed-active');
            sidebar.classList.remove('active');
            desktopToggleBtn.style.display = 'none';
            headerToggleBtn.style.display = 'flex'; // Show header button on mobile
        }
    });
    
    // Initial setting for desktopToggleBtn visibility (since it's hidden by CSS on mobile)
    if (!mediaQueryLarge.matches) {
        desktopToggleBtn.style.display = 'none';
        headerToggleBtn.style.display = 'flex';
    } else {
        desktopToggleBtn.style.display = 'flex';


    // --- Profile Dropdown ---
    const profileAvatar = document.querySelector('.profile-avatar');
    const profileDropdown = document.querySelector('.profile-dropdown');

    // Toggle dropdown on click (mobile/touch)
    profileAvatar.addEventListener('click', function(e) {
        e.stopPropagation(); // prevent immediate close
        if (profileDropdown.style.display === 'flex') {
            profileDropdown.style.display = 'none';
        } else {
            profileDropdown.style.display = 'flex';
        }
    });

    // Close dropdown when clicking outside
    document.addEventListener('click', function() {
        profileDropdown.style.display = 'none';
    });


}

