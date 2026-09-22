const selectBox = document.getElementById("selectBox");
const dropdown = document.getElementById("dropdown");
const toggleBtn = document.getElementById("toggleBtn");
const selectedItems = document.getElementById("selectedItems");
const selectedCount = document.getElementById("selectedCount");
const checkboxes = document.querySelectorAll(".option input");
const skills = {
    HTML: { icon: "ri-html5-fill", class: "html" },
    CSS: { icon: "ri-css3-fill", class: "css" },
    JavaScript: { icon: "ri-javascript-fill", class: "js" },
    React: { icon: "ri-reactjs-line", class: "react" },
    "Vue.js": { icon: "ri-vuejs-line", class: "vue" },
    Angular: { icon: "ri-angularjs-line", class: "angular" },
    "Node.js": { icon: "ri-nodejs-line", class: "node" },
    Python: { icon: "ri-code-box-line", class: "python" },
};
selectBox.addEventListener("click", () => {
    dropdown.classList.toggle("active");
    toggleBtn.classList.toggle("active");
});
function renderSelected() {
    selectedItems.innerHTML = "";
    let total = 0;
    checkboxes.forEach((box) => {
        if (!box.checked) return;
        total++;
        const skill = skills[box.value];
        const chip = document.createElement("div");
        chip.className = "chip";
        chip.innerHTML = `

            <div class="chip-icon ${skill.class}">
                <i class="${skill.icon}"></i>
            </div>

            <span class="chip-text">
                ${box.value}
            </span>

            <div
                class="remove-chip"
                data-value="${box.value}">

                <i class="ri-close-line"></i>

            </div>

        `;
        selectedItems.appendChild(chip);
    });
    if (total === 0) {
        selectedItems.innerHTML = `

            <div class="empty">

                <i class="ri-add-circle-line"></i>

                <span>Select Skills</span>

            </div>

        `;
    }
    selectedCount.textContent = `${total} Selected`;
}
checkboxes.forEach((box) => {
    box.addEventListener("change", () => {
        renderSelected();
    });
});
renderSelected();
const searchInput = document.getElementById("searchInput");
const options = document.querySelectorAll(".option");
const groups = document.querySelectorAll(".group");
searchInput.addEventListener("input", (e) => {
    const value = e.target.value.toLowerCase().trim();
    options.forEach((option) => {
        const title = option.querySelector("h4").textContent.toLowerCase();
        const desc = option.querySelector("p").textContent.toLowerCase();
        const match = title.includes(value) || desc.includes(value);
        option.style.display = match ? "flex" : "none";
    });
    groups.forEach((group) => {
        const items = group.querySelectorAll(".option");
        let hasVisible = !1;
        items.forEach((item) => {
            if (item.style.display !== "none") {
                hasVisible = !0;
            }
        });
        group.style.display = hasVisible ? "block" : "none";
    });
});
selectedItems.addEventListener("click", (e) => {
    const btn = e.target.closest(".remove-chip");
    if (!btn) return;
    const value = btn.dataset.value;
    const checkbox = [...checkboxes].find((box) => box.value === value);
    if (checkbox) {
        checkbox.checked = !1;
    }
    renderSelected();
});
document.addEventListener("click", (e) => {
    const isInside = e.target.closest(".multi-select");
    if (!isInside) {
        dropdown.classList.remove("active");
        toggleBtn.classList.remove("active");
    }
});
document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
        dropdown.classList.remove("active");
        toggleBtn.classList.remove("active");
    }
});
const clearBtn = document.getElementById("clearBtn");
clearBtn.addEventListener("click", () => {
    checkboxes.forEach((box) => {
        box.checked = !1;
    });
    renderSelected();
});
const applyBtn = document.getElementById("applyBtn");
applyBtn.addEventListener("click", () => {
    dropdown.classList.remove("active");
    toggleBtn.classList.remove("active");
});
function syncUI() {
    checkboxes.forEach((box) => {
        const option = box.closest(".option");
        if (box.checked) {
            option.classList.add("selected");
        } else {
            option.classList.remove("selected");
        }
    });
}
const originalRender = renderSelected;
renderSelected = function () {
    originalRender();
    syncUI();
};
renderSelected();