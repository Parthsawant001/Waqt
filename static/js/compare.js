// Weighted Comparison Algorithm Dynamic Slider Recalculation
document.addEventListener('DOMContentLoaded', () => {
  const sliders = document.querySelectorAll('.weight-slider');
  const normalizeBtn = document.getElementById('normalize-weights-btn');

  function updateWeights() {
    let r = parseFloat(document.getElementById('slider-rating')?.value || 30);
    let d = parseFloat(document.getElementById('slider-distance')?.value || 25);
    let p = parseFloat(document.getElementById('slider-price')?.value || 20);
    let w = parseFloat(document.getElementById('slider-wait')?.value || 25);

    const total = r + d + p + w;
    document.getElementById('val-rating').textContent = `${r}%`;
    document.getElementById('val-distance').textContent = `${d}%`;
    document.getElementById('val-price').textContent = `${p}%`;
    document.getElementById('val-wait').textContent = `${w}%`;
    document.getElementById('total-weight-display').textContent = `Total Weight: ${Math.round(total)}%`;
  }

  sliders.forEach(sl => sl.addEventListener('input', updateWeights));
  updateWeights();
});
