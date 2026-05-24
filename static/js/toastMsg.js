function showToast(message, type="success") {
    const toastBox = document.getElementById("toastBox");

    const toast = document.createElement("div");
    toast.className = `alert alert-${type} shadow`;
    toast.innerText = message;

    toastBox.appendChild(toast);

    setTimeout(() => {
        toast.remove();
    }, 3000);
}