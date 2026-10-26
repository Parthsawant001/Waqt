/**
 * Waqt (वेळ) - Multi-Criteria Comparison Algorithm & Google Maps Controller
 * Algorithm 4 (MCDA): Transparent, deterministic multi-criteria scoring
 * Features:
 * - Real-time zero-latency slider recalculation
 * - Side-by-side comparative matrix (up to 4 spots)
 * - Automated best-in-class winner detection
 * - Interactive Google Maps synchronization with custom pins
 * - Departure Hub & GPS location switcher
 */

document.addEventListener('DOMContentLoaded', () => {
  'use strict';

  // 1. Data Initialization
  const dataElement = document.getElementById('all-compare-items-data');
  if (!dataElement) return;

  let rawItems = [];
  try {
    rawItems = JSON.parse(dataElement.textContent);
  } catch (e) {
    console.error('Waqt: Failed to parse compare items payload', e);
    return;
  }

  // Reference coordinates
  let activeUserLat = 19.4632;
  let activeUserLon = 72.7845;

  const hubSelect = document.getElementById('hub-location-select');
  if (hubSelect && hubSelect.value) {
    const parts = hubSelect.value.split(',');
    if (parts.length === 2) {
      activeUserLat = parseFloat(parts[0]);
      activeUserLon = parseFloat(parts[1]);
    }
  }

  // Selected for side-by-side comparison (IDs)
  let selectedIds = new Set();
  rawItems.forEach(item => {
    if (item.selected) selectedIds.add(item.id);
  });
  // Default to top 2 if none selected
  if (selectedIds.size === 0 && rawItems.length >= 2) {
    selectedIds.add(rawItems[0].id);
    selectedIds.add(rawItems[1].id);
  }

  // Sliders
  const sliderRating = document.getElementById('slider-rating');
  const sliderDistance = document.getElementById('slider-distance');
  const sliderPrice = document.getElementById('slider-price');
  const sliderWait = document.getElementById('slider-wait');

  const valRating = document.getElementById('val-rating');
  const valDistance = document.getElementById('val-distance');
  const valPrice = document.getElementById('val-price');
  const valWait = document.getElementById('val-wait');
  const totalWeightDisplay = document.getElementById('total-weight-display');

  // Containers
  const sideBySideContainer = document.getElementById('side-by-side-container');
  const leaderboardContainer = document.getElementById('ranked-leaderboard-list');
  const addSelect = document.getElementById('add-to-compare-select');
  const compareAllTopBtn = document.getElementById('btn-compare-all-top');
  const btnUseGps = document.getElementById('btn-use-gps');
  const coordsDisplay = document.getElementById('active-coords-display');

  // 2. Mathematical Algorithm Implementations
  const MAX_DISTANCE_KM = 35.0;
  const MAX_WAIT_MINUTES = 90.0;

  function haversineDistance(lat1, lon1, lat2, lon2) {
    const R = 6371.0088; // Earth radius in km
    const toRad = deg => deg * (Math.PI / 180);
    const dLat = toRad(lat2 - lat1);
    const dLon = toRad(lon2 - lon1);
    const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
              Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) *
              Math.sin(dLon / 2) * Math.sin(dLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(Math.min(1, a)), Math.sqrt(Math.max(0, 1 - a)));
    return parseFloat((R * c).toFixed(1));
  }

  function computeWaqtScore(item, userLat, userLon, wR, wD, wP, wW) {
    const sumW = wR + wD + wP + wW;
    const normR = sumW > 0 ? (wR / sumW) : 0.25;
    const normD = sumW > 0 ? (wD / sumW) : 0.25;
    const normP = sumW > 0 ? (wP / sumW) : 0.25;
    const normW = sumW > 0 ? (wW / sumW) : 0.25;

    // S_rating: clamp(rating / 5.0, 0, 1)
    const sR = Math.max(0, Math.min(1, item.rating / 5.0));

    // S_distance: 1.0 - min(1.0, dist / 35.0)
    const dist = haversineDistance(userLat, userLon, item.lat, item.lon);
    const sD = Math.max(0, 1.0 - Math.min(1.0, dist / MAX_DISTANCE_KM));

    // S_price: 1.0 - ((tier - 1) / 3.0)
    const sP = Math.max(0, 1.0 - ((item.price_tier - 1) / 3.0));

    // S_wait: 1.0 - min(1.0, wait / 90.0)
    const wait = item.is_connected ? (item.wait_minutes || 0) : 15;
    const sW = Math.max(0, 1.0 - Math.min(1.0, wait / MAX_WAIT_MINUTES));

    const aggregate = (normR * sR) + (normD * sD) + (normP * sP) + (normW * sW);
    const finalScore = Math.round(aggregate * 100);

    return {
      waqt_score: finalScore,
      distance_km: dist,
      breakdown: {
        rating_contribution: (normR * sR * 100).toFixed(1),
        distance_contribution: (normD * sD * 100).toFixed(1),
        price_contribution: (normP * sP * 100).toFixed(1),
        wait_contribution: (normW * sW * 100).toFixed(1),
        rating_pct: Math.round(sR * 100),
        distance_pct: Math.round(sD * 100),
        price_pct: Math.round(sP * 100),
        wait_pct: Math.round(sW * 100),
      }
    };
  }

  // 3. Google Maps Instance
  let compareMapInstance = null;

  function initCompareMap(rankedList) {
    const pins = rankedList.map((item, idx) => ({
      id: item.id,
      name: item.name,
      slug: item.slug,
      locality: item.locality,
      cuisine: item.cuisine,
      price_range: item.price_range,
      rating: item.rating,
      lat: item.lat,
      lon: item.lon,
      is_connected: item.is_connected,
      available_tables: item.available_tables,
      wait_minutes: item.wait_minutes,
      phone: item.phone,
      waqt_score: item.calculated.waqt_score,
      distance_km: item.calculated.distance_km
    }));

    if (window.WaqtMaps) {
      compareMapInstance = window.WaqtMaps.initMap({
        containerId: 'compare-map',
        apiKey: window.WAQT_GOOGLE_MAPS_KEY,
        center: [activeUserLat, activeUserLon],
        zoom: 11,
        pins: pins,
        userCoords: { lat: activeUserLat, lon: activeUserLon },
        showRankOnPins: true,
        onPinClick: (pin) => {
          spotlightRestaurant(pin.id);
        }
      });
    }
  }

  function updateMapPins(rankedList) {
    if (!compareMapInstance) return;
    const pins = rankedList.map(item => ({
      id: item.id,
      name: item.name,
      slug: item.slug,
      locality: item.locality,
      cuisine: item.cuisine,
      price_range: item.price_range,
      rating: item.rating,
      lat: item.lat,
      lon: item.lon,
      is_connected: item.is_connected,
      available_tables: item.available_tables,
      wait_minutes: item.wait_minutes,
      phone: item.phone,
      waqt_score: item.calculated.waqt_score,
      distance_km: item.calculated.distance_km
    }));
    compareMapInstance.updatePins(pins);
  }

  function spotlightRestaurant(id) {
    // Highlight in side by side if present
    const col = document.getElementById(`side-col-${id}`);
    if (col) {
      col.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      col.style.transition = 'transform 0.3s ease, border-color 0.3s ease';
      col.style.borderColor = 'var(--turmeric)';
      col.style.transform = 'scale(1.03)';
      setTimeout(() => {
        col.style.transform = 'scale(1)';
      }, 700);
      return;
    }

    // Otherwise highlight in leaderboard
    const row = document.getElementById(`row-restaurant-${id}`);
    if (row) {
      row.scrollIntoView({ behavior: 'smooth', block: 'center' });
      row.style.background = '#FFFBEB';
      row.style.borderColor = 'var(--turmeric)';
      setTimeout(() => {
        row.style.background = '#fff';
      }, 1200);
    }
  }

  // 4. Recalculation Engine
  function recalculateAll() {
    const wR = parseFloat(sliderRating.value) || 0;
    const wD = parseFloat(sliderDistance.value) || 0;
    const wP = parseFloat(sliderPrice.value) || 0;
    const wW = parseFloat(sliderWait.value) || 0;

    const totalWeight = wR + wD + wP + wW;
    valRating.textContent = `${Math.round(wR)}%`;
    valDistance.textContent = `${Math.round(wD)}%`;
    valPrice.textContent = `${Math.round(wP)}%`;
    valWait.textContent = `${Math.round(wW)}%`;
    totalWeightDisplay.textContent = `Raw Weight Total: ${Math.round(totalWeight)}%`;

    // Compute scores for each restaurant
    const scoredList = rawItems.map(item => {
      const calc = computeWaqtScore(item, activeUserLat, activeUserLon, wR, wD, wP, wW);
      return {
        ...item,
        calculated: calc
      };
    });

    // Sort descending by Waqt Score
    scoredList.sort((a, b) => b.calculated.waqt_score - a.calculated.waqt_score);

    // Render Side-by-Side matrix
    renderSideBySide(scoredList);

    // Render Leaderboard
    renderLeaderboard(scoredList);

    // Update Dropdown
    renderAddDropdown(scoredList);

    // Update Map
    updateMapPins(scoredList);
  }

  // 5. Render Side-by-Side Matrix
  function renderSideBySide(rankedList) {
    if (!sideBySideContainer) return;

    const selectedItems = rankedList.filter(item => selectedIds.has(item.id));

    if (selectedItems.length === 0) {
      sideBySideContainer.innerHTML = `
        <div style="background: #fff; border: 1px dashed var(--sand); border-radius: var(--radius-md); padding: 40px; text-align: center; color: var(--driftwood); grid-column: 1 / -1;">
          <p style="font-size: 16px; margin-bottom: 8px;">No restaurants currently selected for side-by-side comparison.</p>
          <p style="font-size: 13px; color: var(--wet-sand); margin: 0;">Select spots from the dropdown above or click "Compare Side-by-Side" on any spot in the ranked leaderboard.</p>
        </div>
      `;
      return;
    }

    // Find winners
    let topScoreId = null, topScore = -1;
    let minWaitId = null, minWait = 999;
    let minDistId = null, minDist = 999;
    let maxRatingId = null, maxRating = -1;

    selectedItems.forEach(item => {
      if (item.calculated.waqt_score > topScore) {
        topScore = item.calculated.waqt_score;
        topScoreId = item.id;
      }
      const wait = item.is_connected ? item.wait_minutes : 99;
      if (wait < minWait) {
        minWait = wait;
        minWaitId = item.id;
      }
      if (item.calculated.distance_km < minDist) {
        minDist = item.calculated.distance_km;
        minDistId = item.id;
      }
      if (item.rating > maxRating) {
        maxRating = item.rating;
        maxRatingId = item.id;
      }
    });

    let html = '';
    selectedItems.forEach(item => {
      const isWinner = item.id === topScoreId;
      const isConnected = item.is_connected;
      const directionsUrl = `https://www.google.com/maps/dir/?api=1&destination=${item.lat},${item.lon}`;

      // Winner badges
      let winnerBadge = '';
      if (isWinner) {
        winnerBadge = `<div class="winner-crown-tag">👑 #1 Waqt Pick</div>`;
      } else if (item.id === minWaitId && isConnected) {
        winnerBadge = `<div class="winner-crown-tag" style="background: #166534;">⚡ Fastest Seating</div>`;
      } else if (item.id === minDistId) {
        winnerBadge = `<div class="winner-crown-tag" style="background: var(--deep-tide);">📍 Closest Spot</div>`;
      } else if (item.id === maxRatingId) {
        winnerBadge = `<div class="winner-crown-tag" style="background: #ea580c;">★ Top Rated</div>`;
      }

      // Capacity chip
      let capacitySection = '';
      if (isConnected) {
        capacitySection = `
          <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 12px; margin-bottom: 16px;">
            <div style="display: flex; justify-content: space-between; font-size: 13px; font-weight: 700; color: #166534;">
              <span>🪑 ${item.available_tables} / ${item.total_tables} Free</span>
              <span>⏱️ ${item.wait_minutes} min wait</span>
            </div>
            <div style="font-size: 11px; color: #15803d; margin-top: 3px;">
              Queue: ${item.waiting_queue} party waiting
            </div>
          </div>
        `;
      } else {
        capacitySection = `
          <div style="background: var(--shell); border: 1px dashed var(--sand); border-radius: 8px; padding: 12px; margin-bottom: 16px;">
            <div style="font-size: 12px; font-weight: 600; color: var(--driftwood);">
              📋 Verified Public Directory Listing
            </div>
            <div style="font-size: 11px; color: var(--wet-sand); margin-top: 2px;">
              Live table capacity disabled until claimed
            </div>
          </div>
        `;
      }

      // Action buttons
      let actionButtons = '';
      if (isConnected) {
        actionButtons = `
          <div style="display: flex; flex-direction: column; gap: 8px; margin-top: auto; padding-top: 16px; border-top: var(--border-subtle);">
            <div style="display: flex; gap: 6px;">
              <a href="/reservations/book/${item.slug}/" class="btn btn-primary btn-sm" style="flex: 1; text-align: center;">Book Table</a>
              <a href="/queue/join/${item.slug}/" class="btn btn-accent btn-sm" style="flex: 1; text-align: center;">Join Queue</a>
            </div>
            <div style="display: flex; gap: 6px;">
              <a href="/restaurants/${item.slug}/" class="btn btn-outline btn-sm" style="flex: 1; text-align: center;">Floor & Menu</a>
              <a href="${directionsUrl}" target="_blank" rel="noopener noreferrer" class="btn btn-outline btn-sm" style="text-align: center;" title="Google Maps Directions">🧭</a>
            </div>
          </div>
        `;
      } else {
        actionButtons = `
          <div style="display: flex; flex-direction: column; gap: 8px; margin-top: auto; padding-top: 16px; border-top: var(--border-subtle);">
            <div style="display: flex; gap: 6px;">
              <a href="/restaurants/${item.slug}/" class="btn btn-primary btn-sm" style="flex: 1; text-align: center;">View Details</a>
              <a href="tel:${item.phone}" class="btn btn-outline btn-sm" style="text-align: center;">Call</a>
            </div>
            <a href="${directionsUrl}" target="_blank" rel="noopener noreferrer" class="btn btn-outline btn-sm" style="text-align: center;">🧭 Directions in Google Maps</a>
          </div>
        `;
      }

      html += `
        <div class="compare-card-col ${isWinner ? 'highlighted-winner' : ''}" id="side-col-${item.id}">
          ${winnerBadge}

          <!-- Header -->
          <div style="padding: 24px 20px 16px 20px; border-bottom: var(--border-subtle); position: relative;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 6px; padding-right: 32px;">
              <span class="locality-badge">${item.locality}</span>
              <button type="button" class="remove-compare-btn" data-remove-id="${item.id}" title="Remove from comparison">×</button>
            </div>
            <h3 style="font-size: 20px; margin: 0 0 4px 0; color: var(--deep-tide); line-height: 1.3;">${item.name}</h3>
            <div style="font-size: 12px; color: var(--wet-sand);">
              ${item.cuisine} &bull; ${item.price_range} &bull; ★ ${item.rating}
            </div>
          </div>

          <!-- Body -->
          <div style="padding: 20px; flex: 1; display: flex; flex-direction: column;">
            
            <!-- Overall Score Badge -->
            <div style="display: flex; align-items: baseline; justify-content: space-between; margin-bottom: 16px; background: #FFFBF5; border: 1px solid #FFE4C4; border-radius: 8px; padding: 12px 16px;">
              <span style="font-size: 12px; text-transform: uppercase; font-weight: 700; color: var(--driftwood);">Waqt Score</span>
              <span style="font-size: 32px; font-family: var(--font-serif); font-weight: 700; color: var(--deep-tide);">
                ${item.calculated.waqt_score} <span style="font-size: 14px; font-weight: 400; color: var(--wet-sand);">/ 100</span>
              </span>
            </div>

            <!-- Proximity & Wait Quick Stat -->
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 16px; text-align: center;">
              <div style="background: #f8fafc; padding: 8px; border-radius: 6px; border: 1px solid #e2e8f0;">
                <div style="font-size: 10px; text-transform: uppercase; color: var(--wet-sand);">Distance</div>
                <div style="font-size: 15px; font-weight: 700; color: var(--deep-tide);">${item.calculated.distance_km} km</div>
              </div>
              <div style="background: #f8fafc; padding: 8px; border-radius: 6px; border: 1px solid #e2e8f0;">
                <div style="font-size: 10px; text-transform: uppercase; color: var(--wet-sand);">Wait Time</div>
                <div style="font-size: 15px; font-weight: 700; color: var(--deep-tide);">${isConnected ? item.wait_minutes + 'm' : 'N/A'}</div>
              </div>
            </div>

            <!-- Live Capacity Status -->
            ${capacitySection}

            <!-- Multi-Criteria Factor Contributions -->
            <div style="display: flex; flex-direction: column; gap: 8px; margin-bottom: 16px;">
              <div class="factor-bar-row">
                <div class="factor-label-wrap">
                  <span>Rating Contribution</span>
                  <span style="color: var(--turmeric);">+${item.calculated.breakdown.rating_contribution}</span>
                </div>
                <div class="metric-progress-track">
                  <div class="metric-progress-fill" style="width: ${item.calculated.breakdown.rating_pct}%; background: var(--turmeric);"></div>
                </div>
              </div>

              <div class="factor-bar-row">
                <div class="factor-label-wrap">
                  <span>Proximity (Distance)</span>
                  <span style="color: var(--deep-tide);">+${item.calculated.breakdown.distance_contribution}</span>
                </div>
                <div class="metric-progress-track">
                  <div class="metric-progress-fill" style="width: ${item.calculated.breakdown.distance_pct}%; background: var(--deep-tide);"></div>
                </div>
              </div>

              <div class="factor-bar-row">
                <div class="factor-label-wrap">
                  <span>Budget Affordability</span>
                  <span style="color: #166534;">+${item.calculated.breakdown.price_contribution}</span>
                </div>
                <div class="metric-progress-track">
                  <div class="metric-progress-fill" style="width: ${item.calculated.breakdown.price_pct}%; background: #166534;"></div>
                </div>
              </div>

              <div class="factor-bar-row">
                <div class="factor-label-wrap">
                  <span>Wait Speed</span>
                  <span style="color: #b91c1c;">+${item.calculated.breakdown.wait_contribution}</span>
                </div>
                <div class="metric-progress-track">
                  <div class="metric-progress-fill" style="width: ${item.calculated.breakdown.wait_pct}%; background: #b91c1c;"></div>
                </div>
              </div>
            </div>

            <!-- CTAs -->
            ${actionButtons}
          </div>
        </div>
      `;
    });

    sideBySideContainer.innerHTML = html;

    // Attach Remove Button Handlers
    const removeBtns = sideBySideContainer.querySelectorAll('.remove-compare-btn');
    removeBtns.forEach(btn => {
      btn.addEventListener('click', (e) => {
        const idToRemove = parseInt(btn.getAttribute('data-remove-id'));
        selectedIds.delete(idToRemove);
        recalculateAll();
      });
    });
  }

  // 6. Render Ranked Leaderboard List
  function renderLeaderboard(rankedList) {
    if (!leaderboardContainer) return;

    let html = '';
    rankedList.forEach((item, index) => {
      const isSelected = selectedIds.has(item.id);
      const isConn = item.is_connected;

      html += `
        <div class="ranked-item-row" id="row-restaurant-${item.id}">
          <div>
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 4px;">
              <span style="font-size: 18px; font-weight: 700; color: var(--turmeric);">#${index + 1}</span>
              <h3 style="font-size: 18px; margin: 0; color: var(--deep-tide);">${item.name}</h3>
            </div>
            <div style="font-size: 12px; color: var(--wet-sand);">
              ${item.locality} &bull; ${item.cuisine} &bull; ${item.price_range} &bull; ★ ${item.rating}
            </div>
          </div>

          <div>
            <div style="font-size: 11px; text-transform: uppercase; color: var(--driftwood);">Overall Waqt Score</div>
            <div style="font-size: 24px; font-family: var(--font-serif); font-weight: 700; color: var(--deep-tide);">
              ${item.calculated.waqt_score} <span style="font-size: 13px; font-weight: 400; color: var(--wet-sand);">/ 100</span>
            </div>
          </div>

          <div>
            <div style="font-size: 11px; text-transform: uppercase; color: var(--driftwood);">Distance & Wait</div>
            <div style="font-size: 13px; font-weight: 600; color: var(--deep-tide); margin-top: 3px;">
              ${item.calculated.distance_km} km &bull; ${isConn ? item.wait_minutes + ' min wait' : 'Directory spot'}
            </div>
          </div>

          <div style="display: flex; flex-direction: column; gap: 3px; font-size: 11px; color: var(--driftwood);">
            <div>Rating: <strong>+${item.calculated.breakdown.rating_contribution}</strong> &bull; Dist: <strong>+${item.calculated.breakdown.distance_contribution}</strong></div>
            <div>Price: <strong>+${item.calculated.breakdown.price_contribution}</strong> &bull; Wait: <strong>+${item.calculated.breakdown.wait_contribution}</strong></div>
          </div>

          <div style="display: flex; flex-direction: column; gap: 6px;">
            <a href="/restaurants/${item.slug}/" class="btn btn-outline btn-sm" style="text-align: center;">
              View Details
            </a>
            <button type="button" class="btn btn-sm ${isSelected ? 'btn-accent' : 'btn-primary'} btn-toggle-side-by-side" data-id="${item.id}" style="font-size: 11px; white-space: nowrap;">
              ${isSelected ? '✓ In Comparison' : '+ Compare'}
            </button>
          </div>
        </div>
      `;
    });

    leaderboardContainer.innerHTML = html;

    // Attach Toggle Side-by-Side Handlers
    const toggleBtns = leaderboardContainer.querySelectorAll('.btn-toggle-side-by-side');
    toggleBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        const id = parseInt(btn.getAttribute('data-id'));
        if (selectedIds.has(id)) {
          selectedIds.delete(id);
        } else {
          if (selectedIds.size >= 4) {
            alert('You can compare up to 4 restaurants side-by-side. Please remove one first.');
            return;
          }
          selectedIds.add(id);
        }
        recalculateAll();
      });
    });
  }

  // 7. Render Add to Compare Dropdown
  function renderAddDropdown(rankedList) {
    if (!addSelect) return;

    let html = '<option value="">+ Add Restaurant to Compare...</option>';
    rankedList.forEach(item => {
      const isSelected = selectedIds.has(item.id);
      if (!isSelected) {
        html += `<option value="${item.id}">${item.name} (${item.locality}) — Score: ${item.calculated.waqt_score}</option>`;
      }
    });
    addSelect.innerHTML = html;
  }

  if (addSelect) {
    addSelect.addEventListener('change', () => {
      const chosenId = parseInt(addSelect.value);
      if (chosenId) {
        if (selectedIds.size >= 4) {
          alert('You can compare up to 4 restaurants side-by-side. Please remove one first.');
          addSelect.value = '';
          return;
        }
        selectedIds.add(chosenId);
        recalculateAll();
        addSelect.value = '';
      }
    });
  }

  // "Compare Top 3" Button
  if (compareAllTopBtn) {
    compareAllTopBtn.addEventListener('click', () => {
      const wR = parseFloat(sliderRating.value) || 0;
      const wD = parseFloat(sliderDistance.value) || 0;
      const wP = parseFloat(sliderPrice.value) || 0;
      const wW = parseFloat(sliderWait.value) || 0;

      const scoredList = rawItems.map(item => ({
        ...item,
        calculated: computeWaqtScore(item, activeUserLat, activeUserLon, wR, wD, wP, wW)
      }));
      scoredList.sort((a, b) => b.calculated.waqt_score - a.calculated.waqt_score);

      selectedIds.clear();
      scoredList.slice(0, 3).forEach(item => selectedIds.add(item.id));
      recalculateAll();
    });
  }

  // 8. Preset Weight Buttons
  const presetButtons = document.querySelectorAll('.preset-btn');
  presetButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      presetButtons.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      const r = btn.getAttribute('data-r');
      const d = btn.getAttribute('data-d');
      const p = btn.getAttribute('data-p');
      const w = btn.getAttribute('data-w');

      sliderRating.value = r;
      sliderDistance.value = d;
      sliderPrice.value = p;
      sliderWait.value = w;

      recalculateAll();
    });
  });

  // 9. Slider Input Listeners
  [sliderRating, sliderDistance, sliderPrice, sliderWait].forEach(slider => {
    if (slider) {
      slider.addEventListener('input', () => {
        presetButtons.forEach(b => b.classList.remove('active'));
        recalculateAll();
      });
    }
  });

  // 10. Reference Location Selector
  if (hubSelect) {
    hubSelect.addEventListener('change', () => {
      const parts = hubSelect.value.split(',');
      if (parts.length === 2) {
        activeUserLat = parseFloat(parts[0]);
        activeUserLon = parseFloat(parts[1]);
        if (coordsDisplay) {
          coordsDisplay.textContent = `Reference: ${activeUserLat.toFixed(4)}, ${activeUserLon.toFixed(4)}`;
        }
        recalculateAll();
      }
    });
  }

  // 11. GPS Location Button
  if (btnUseGps) {
    btnUseGps.addEventListener('click', () => {
      if (!navigator.geolocation) {
        alert('Geolocation is not supported by your browser.');
        return;
      }
      btnUseGps.textContent = '⏳ Locating...';
      navigator.geolocation.getCurrentPosition(
        pos => {
          activeUserLat = parseFloat(pos.coords.latitude.toFixed(4));
          activeUserLon = parseFloat(pos.coords.longitude.toFixed(4));
          btnUseGps.textContent = '📍 GPS Active';

          // Add or update option in select
          let gpsOpt = document.getElementById('hub-gps-option');
          if (!gpsOpt) {
            gpsOpt = document.createElement('option');
            gpsOpt.id = 'hub-gps-option';
            hubSelect.prepend(gpsOpt);
          }
          gpsOpt.value = `${activeUserLat},${activeUserLon}`;
          gpsOpt.textContent = `📍 My Current GPS (${activeUserLat}, ${activeUserLon})`;
          hubSelect.value = gpsOpt.value;

          if (coordsDisplay) {
            coordsDisplay.textContent = `Reference: ${activeUserLat}, ${activeUserLon} (Live GPS)`;
          }

          recalculateAll();
        },
        err => {
          btnUseGps.textContent = '🧭 GPS';
          alert(`Unable to retrieve GPS location: ${err.message}`);
        },
        { enableHighAccuracy: true, timeout: 8000 }
      );
    });
  }

  // 12. Initial Run
  const initialScored = rawItems.map(item => ({
    ...item,
    calculated: computeWaqtScore(
      item, activeUserLat, activeUserLon,
      parseFloat(sliderRating?.value || 30),
      parseFloat(sliderDistance?.value || 25),
      parseFloat(sliderPrice?.value || 20),
      parseFloat(sliderWait?.value || 25)
    )
  }));
  initialScored.sort((a, b) => b.calculated.waqt_score - a.calculated.waqt_score);

  // Initialize Map
  initCompareMap(initialScored);

  // Recalculate & Render initial state
  recalculateAll();
});
