document.addEventListener('DOMContentLoaded', function () {
    const sidebarOpener = document.getElementById('sidebarOpener');
    const overlay = document.createElement('div');
    overlay.classList.add('overlay');
    document.body.appendChild(overlay);

    let isSidebarOpen = false; // Sidebar is hidden by default

    // Open sidebar when the opener is clicked
    sidebarOpener.addEventListener('click', function () {
        toggleSidebar(); // Open sidebar only when user clicks the opener
    });

    // Close sidebar when clicking outside of it (on the overlay)
    overlay.addEventListener('click', function () {
        closeSidebar(); // Close the sidebar when user clicks the overlay
    });

    function toggleSidebar() {
        if (!isSidebarOpen) {
            openSidebar(); // Only open if it's closed
        } else {
            closeSidebar(); // Close it if it's already open
        }
    }

    function openSidebar() {
        isSidebarOpen = true;
        document.body.classList.add('sidebar-opened'); // Add class to open sidebar
        overlay.classList.add('active');  // Show the overlay to darken the rest of the page
    }

    function closeSidebar() {
        isSidebarOpen = false;
        document.body.classList.remove('sidebar-opened'); // Remove class to close sidebar
        overlay.classList.remove('active');  // Hide the overlay
    }

    // Switch between layers
    window.showLayer = function (layerId) {
        const layers = ['dashboardLayer','mainLayer'];
        
        // Hide all layers first
        layers.forEach(id => {
            const layer = document.getElementById(id);
            layer.style.display = 'none';  // Hide each layer
        });

        // Show the selected layer
        const selectedLayer = document.getElementById(layerId + 'Layer');
        if (selectedLayer) {
            selectedLayer.style.display = 'block';  // Show the target layer
        }
    };

    // Show dashboardLayer first by default without opening the sidebar
    showLayer('dashboard');
});
