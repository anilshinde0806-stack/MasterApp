

const button = document.querySelector(".button");
  let hue = 0;

  // Animate hue to sync with rainbow text
  function animateHue() {
    hue = (hue + 1) % 360;
    button.style.setProperty("--hue", hue);
    requestAnimationFrame(animateHue);
  }
  animateHue();
  // Mouse move = glow follow
  button.addEventListener("mousemove", (e) => {
    const rect = button.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * 100;
    const y = ((e.clientY - rect.top) / rect.height) * 100;
    button.style.setProperty("--x", x + "%");
    button.style.setProperty("--y", y + "%");
  });

  // Click = ripple burst
  button.addEventListener("click", (e) => {
    const rect = button.getBoundingClientRect();
    const ripple = document.createElement("span");

    const size = Math.max(rect.width, rect.height);
    ripple.style.width = ripple.style.height = size + "px";

    ripple.style.left = e.clientX - rect.left - size / 2 + "px";
    ripple.style.top = e.clientY - rect.top - size / 2 + "px";
    ripple.classList.add("ripple");

    button.appendChild(ripple);

    setTimeout(() => ripple.remove(), 600);
  });
