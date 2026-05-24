// Toggle sidebar

document.addEventListener("DOMContentLoaded", function () {

    const toggleBtn = document.getElementById("toggleSidebar");
    const sidebar = document.querySelector(".sidebar");

    if (!toggleBtn) {
        console.error("toggleSidebar button NOT found");
        return;
    }

    if (!sidebar) {
        console.error("sidebar NOT found");
        return;
    }

    toggleBtn.addEventListener("click", function () {
        console.log("Sidebar toggle clicked"); // debug
        sidebar.classList.toggle("collapsed");

    });

});

// Submenu toggle
document.querySelectorAll('.menu-link').forEach(link => {
    link.addEventListener('click', function () {
        const currentItem = this.closest('.menu-item');

        // Close all other menu items
        document.querySelectorAll('.menu-item').forEach(item => {
            if (item !== currentItem) {
                item.classList.remove('active');
            }
        });

        // Toggle current one
        currentItem.classList.toggle('active');
    });
});

// new script



document.addEventListener("click", function (e) {

    const link = e.target.closest(".menu-link");
    if (!link) return;

    const item = link.closest(".menu-item");
    const hasSubmenu = item.querySelector(".submenu");

    // If it has submenu → toggle accordion
    if (hasSubmenu) {
        e.preventDefault();

        // close others
        document.querySelectorAll(".menu-item").forEach(el => {
            if (el !== item) el.classList.remove("active");
        });

        item.classList.toggle("active");
    }
});
