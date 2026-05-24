document.addEventListener("DOMContentLoaded", function() {
  const marquee = document.getElementById('productMarquee');
  if (!marquee) return;

  const track = marquee.querySelector('.marquee-track');
  const first = track.querySelector('.marquee-content');
  const second = track.querySelectorAll('.marquee-content')[1];

  // Clone products for loop effect
  second.innerHTML = first.innerHTML;

  // Calculate animation duration based on width
  const totalWidth = first.scrollWidth;
  const speed = 60; // px/sec
  const duration = totalWidth / speed;
  track.style.setProperty('--dur', duration + 's');
});
