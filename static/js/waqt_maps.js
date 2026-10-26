/**
 * Waqt (वेळ) Unified Map Service
 * Integrates Google Maps JavaScript API with high-reliability fallback.
 * Supports:
 * - Dynamic Marker Management
 * - Live Pilot vs. Directory custom pins
 * - User Location Beacon
 * - Rich Editorial InfoWindows
 * - Directions links
 */

window.WaqtMaps = (function () {
  'use strict';

  let googleMapsLoaded = false;
  let googleMapsFailed = false;
  let activeInstances = {};

  // Custom Warm Coastal Google Map styling
  const coastalMapStyle = [
    { elementType: 'geometry', stylers: [{ color: '#f5f2eb' }] },
    { elementType: 'labels.text.stroke', stylers: [{ color: '#ffffff' }] },
    { elementType: 'labels.text.fill', stylers: [{ color: '#2c4041' }] },
    {
      featureType: 'administrative.locality',
      elementType: 'labels.text.fill',
      stylers: [{ color: '#0F2C2D' }, { weight: 1.2 }]
    },
    {
      featureType: 'poi',
      elementType: 'labels.text.fill',
      stylers: [{ color: '#687b7c' }]
    },
    {
      featureType: 'poi.park',
      elementType: 'geometry',
      stylers: [{ color: '#e2ecd9' }]
    },
    {
      featureType: 'road',
      elementType: 'geometry',
      stylers: [{ color: '#ffffff' }]
    },
    {
      featureType: 'road',
      elementType: 'geometry.stroke',
      stylers: [{ color: '#dfd8ca' }]
    },
    {
      featureType: 'road.highway',
      elementType: 'geometry',
      stylers: [{ color: '#eddac3' }]
    },
    {
      featureType: 'road.highway',
      elementType: 'geometry.stroke',
      stylers: [{ color: '#deb887' }]
    },
    {
      featureType: 'water',
      elementType: 'geometry',
      stylers: [{ color: '#a5c9cb' }]
    },
    {
      featureType: 'water',
      elementType: 'labels.text.fill',
      stylers: [{ color: '#102C2D' }]
    }
  ];

  /**
   * Loads Google Maps JS API script if not already loaded.
   */
  function loadGoogleMapsScript(apiKey) {
    return new Promise((resolve, reject) => {
      if (window.google && window.google.maps) {
        googleMapsLoaded = true;
        return resolve();
      }

      if (!apiKey) {
        googleMapsFailed = true;
        return reject(new Error('No Google Maps API Key provided'));
      }

      // Check if script tag is already in DOM
      if (document.getElementById('google-maps-script')) {
        const checkInterval = setInterval(() => {
          if (window.google && window.google.maps) {
            clearInterval(checkInterval);
            googleMapsLoaded = true;
            resolve();
          } else if (googleMapsFailed) {
            clearInterval(checkInterval);
            reject(new Error('Google Maps script failed'));
          }
        }, 100);
        return;
      }

      // Listen for Google Maps Authentication failure (e.g. billing or key restrictions)
      const prevAuthFailure = window.gm_authFailure;
      window.gm_authFailure = function () {
        console.warn('Waqt: Google Maps API key authentication error / billing required. Falling back to resilient Leaflet tiles.');
        googleMapsFailed = true;
        if (typeof prevAuthFailure === 'function') prevAuthFailure();
        // Trigger fallback for all active instances
        Object.values(activeInstances).forEach(inst => {
          if (inst && typeof inst.fallbackToLeaflet === 'function') {
            inst.fallbackToLeaflet();
          }
        });
      };

      const script = document.createElement('script');
      script.id = 'google-maps-script';
      script.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(apiKey)}&libraries=places,geometry`;
      script.async = true;
      script.defer = true;

      script.onload = () => {
        googleMapsLoaded = true;
        resolve();
      };

      script.onerror = (err) => {
        console.warn('Waqt: Google Maps script failed to load. Will fallback to Leaflet.', err);
        googleMapsFailed = true;
        reject(err);
      };

      document.head.appendChild(script);
    });
  }

  /**
   * Creates custom SVG marker icon for Google Maps
   */
  function getGoogleMarkerIcon(isLive, rankText) {
    const bgColor = isLive ? '#D9822B' : '#4A6061';
    const labelColor = '#FFFFFF';
    const textHtml = rankText ? `<text x="14" y="16" fill="${labelColor}" font-size="10" font-family="sans-serif" font-weight="bold" text-anchor="middle">${rankText}</text>` : `<circle cx="14" cy="14" r="4.5" fill="#FFFFFF"/>`;

    const svg = `
      <svg xmlns="http://www.w3.org/2000/svg" width="28" height="36" viewBox="0 0 28 36">
        <path d="M14 0 C6.27 0 0 6.27 0 14 C0 24.5 14 36 14 36 C14 36 28 24.5 28 14 C28 6.27 21.73 0 14 0 Z" fill="${bgColor}" stroke="#FFFFFF" stroke-width="2"/>
        ${textHtml}
      </svg>
    `;

    return {
      url: 'data:image/svg+xml;charset=UTF-8,' + encodeURIComponent(svg),
      scaledSize: new google.maps.Size(28, 36),
      anchor: new google.maps.Point(14, 36)
    };
  }

  /**
   * Generates Rich HTML for InfoWindow
   */
  function buildInfoWindowContent(pin, userLat, userLon) {
    const isLive = pin.is_connected;
    const directionsUrl = `https://www.google.com/maps/dir/?api=1&destination=${pin.lat},${pin.lon}`;
    
    let statusBadge = isLive
      ? `<span style="background: #1D6F42; color: #fff; font-size: 10px; font-weight: 700; padding: 2px 7px; border-radius: 999px;">LIVE ACTIVE</span>`
      : `<span style="background: #4A6061; color: #fff; font-size: 10px; font-weight: 600; padding: 2px 7px; border-radius: 999px;">DIRECTORY</span>`;

    let scoreBadge = pin.waqt_score !== undefined
      ? `<span style="background: #FFF7ED; border: 1px solid #D9822B; color: #D9822B; font-weight: 700; font-size: 11px; padding: 2px 6px; border-radius: 4px;">Score: ${pin.waqt_score}/100</span>`
      : `<span style="background: #FFF7ED; color: #D9822B; font-weight: 700; font-size: 11px;">★ ${pin.rating || 4.2}</span>`;

    let liveInfo = '';
    if (isLive) {
      liveInfo = `
        <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 6px; padding: 6px 10px; margin: 8px 0; font-size: 11px; display: flex; justify-content: space-between;">
          <span style="color: #166534; font-weight: 600;">🪑 ${pin.available_tables || 0} Tables Free</span>
          <span style="color: #166534; font-weight: 600;">⏱️ ${pin.wait_minutes || 0}m Wait</span>
        </div>
      `;
    } else {
      liveInfo = `
        <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 6px 10px; margin: 8px 0; font-size: 11px; color: #64748b;">
          Verified directory listing &bull; Call: ${pin.phone || 'Available on request'}
        </div>
      `;
    }

    let actions = `
      <div style="display: flex; gap: 6px; margin-top: 8px;">
        <a href="/restaurants/${pin.slug}/" style="flex: 1; background: #0F2C2D; color: #fff; text-decoration: none; padding: 6px 10px; border-radius: 4px; font-size: 11px; font-weight: 600; text-align: center;">View Details</a>
        <a href="${directionsUrl}" target="_blank" rel="noopener noreferrer" style="background: #D9822B; color: #fff; text-decoration: none; padding: 6px 10px; border-radius: 4px; font-size: 11px; font-weight: 600; text-align: center;" title="Directions in Google Maps">🧭 Directions</a>
      </div>
    `;

    return `
      <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; min-width: 210px; max-width: 260px; padding: 4px 2px; color: #0F2C2D;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
          ${statusBadge}
          ${scoreBadge}
        </div>
        <h4 style="margin: 4px 0 2px 0; font-size: 14px; font-weight: 700; color: #0F2C2D; line-height: 1.3;">${pin.name}</h4>
        <div style="font-size: 11px; color: #64748b; margin-bottom: 2px;">
          ${pin.locality || ''} &bull; ${pin.cuisine || 'Coastal Seafood'} &bull; ${pin.price_range || '₹₹'}
        </div>
        ${pin.distance_km ? `<div style="font-size: 11px; color: #D9822B; font-weight: 600;">📏 ${pin.distance_km} km away</div>` : ''}
        ${liveInfo}
        ${actions}
      </div>
    `;
  }

  /**
   * Initializes a Waqt Map Instance on a container
   */
  function initMap(config) {
    const {
      containerId,
      apiKey,
      center = [19.68, 72.78],
      zoom = 11,
      pins = [],
      userCoords = null,
      onPinClick = null,
      showRankOnPins = false
    } = config;

    const container = document.getElementById(containerId);
    if (!container) return null;

    let gMap = null;
    let lMap = null;
    let gMarkers = [];
    let lMarkers = [];
    let currentInfoWindow = null;
    let userMarker = null;

    const instance = {
      containerId,
      isGoogle: false,
      map: null,
      updatePins: function (newPins, newCenter, newZoom) {
        if (this.isGoogle && gMap) {
          updateGooglePins(newPins, newCenter, newZoom);
        } else if (lMap) {
          updateLeafletPins(newPins, newCenter, newZoom);
        }
      },
      panTo: function (lat, lon, zoomLevel = 15) {
        if (this.isGoogle && gMap) {
          gMap.panTo({ lat, lng: lon });
          gMap.setZoom(zoomLevel);
        } else if (lMap) {
          lMap.setView([lat, lon], zoomLevel);
        }
      },
      fallbackToLeaflet: function () {
        if (this.isGoogle) {
          this.isGoogle = false;
          container.innerHTML = '';
          setupLeaflet(pins);
        }
      }
    };

    activeInstances[containerId] = instance;

    // Try Google Maps first
    loadGoogleMapsScript(apiKey)
      .then(() => {
        if (googleMapsFailed) {
          setupLeaflet(pins);
        } else {
          setupGoogleMap(pins);
        }
      })
      .catch(() => {
        setupLeaflet(pins);
      });

    // Setup Google Map implementation
    function setupGoogleMap(initialPins) {
      try {
        instance.isGoogle = true;
        container.innerHTML = '';

        const mapOptions = {
          center: { lat: center[0], lng: center[1] },
          zoom: zoom,
          styles: coastalMapStyle,
          mapTypeControl: false,
          streetViewControl: false,
          fullscreenControl: true,
          zoomControl: true,
          gestureHandling: 'cooperative'
        };

        gMap = new google.maps.Map(container, mapOptions);
        instance.map = gMap;
        currentInfoWindow = new google.maps.InfoWindow();

        // Add subtle indicator badge
        const badge = document.createElement('div');
        badge.style.cssText = 'position: absolute; bottom: 8px; left: 8px; background: rgba(255,255,255,0.92); border: 1px solid #dfd8ca; padding: 3px 8px; border-radius: 4px; font-size: 10px; font-weight: 600; color: #0F2C2D; z-index: 5; pointer-events: none; box-shadow: 0 1px 4px rgba(0,0,0,0.1);';
        badge.innerHTML = '🗺️ Google Maps Active';
        container.appendChild(badge);

        // User Location Beacon
        if (userCoords && userCoords.lat && userCoords.lon) {
          addUserLocationGoogle(userCoords.lat, userCoords.lon);
        }

        updateGooglePins(initialPins);
      } catch (e) {
        console.warn('Waqt: Failed to initialize Google Map object, switching to Leaflet:', e);
        setupLeaflet(initialPins);
      }
    }

    function addUserLocationGoogle(lat, lon) {
      const userSvg = `
        <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 22 22">
          <circle cx="11" cy="11" r="10" fill="rgba(37, 99, 235, 0.25)" stroke="#2563EB" stroke-width="2"/>
          <circle cx="11" cy="11" r="5" fill="#2563EB"/>
        </svg>
      `;

      userMarker = new google.maps.Marker({
        position: { lat: parseFloat(lat), lng: parseFloat(lon) },
        map: gMap,
        title: 'Your Location',
        icon: {
          url: 'data:image/svg+xml;charset=UTF-8,' + encodeURIComponent(userSvg),
          scaledSize: new google.maps.Size(22, 22),
          anchor: new google.maps.Point(11, 11)
        },
        zIndex: 999
      });
    }

    function updateGooglePins(pinsData, fitCenter, fitZoom) {
      // Clear existing markers
      gMarkers.forEach(m => m.setMap(null));
      gMarkers = [];

      if (!pinsData || !pinsData.length) return;

      const bounds = new google.maps.LatLngBounds();
      if (userCoords && userCoords.lat && userCoords.lon) {
        bounds.extend(new google.maps.LatLng(userCoords.lat, userCoords.lon));
      }

      pinsData.forEach((p, idx) => {
        const rankStr = showRankOnPins ? `${idx + 1}` : null;
        const icon = getGoogleMarkerIcon(p.is_connected, rankStr);

        const marker = new google.maps.Marker({
          position: { lat: parseFloat(p.lat), lng: parseFloat(p.lon) },
          map: gMap,
          title: p.name,
          icon: icon
        });

        marker.restaurantData = p;

        marker.addListener('click', () => {
          const content = buildInfoWindowContent(p, userCoords ? userCoords.lat : null, userCoords ? userCoords.lon : null);
          currentInfoWindow.setContent(content);
          currentInfoWindow.open(gMap, marker);

          if (typeof onPinClick === 'function') {
            onPinClick(p, idx);
          }
        });

        gMarkers.push(marker);
        bounds.extend(marker.getPosition());
      });

      if (fitCenter && fitZoom) {
        gMap.setCenter({ lat: fitCenter[0], lng: fitCenter[1] });
        gMap.setZoom(fitZoom);
      } else if (pinsData.length > 1) {
        gMap.fitBounds(bounds, { top: 40, right: 40, bottom: 40, left: 40 });
      } else if (pinsData.length === 1) {
        gMap.setCenter({ lat: parseFloat(pinsData[0].lat), lng: parseFloat(pinsData[0].lon) });
        gMap.setZoom(14);
      }
    }

    // Setup Leaflet Implementation (Resilient Backup)
    function setupLeaflet(initialPins) {
      instance.isGoogle = false;
      container.innerHTML = '';

      if (typeof L === 'undefined') {
        console.error('Waqt: Leaflet library not found.');
        return;
      }

      lMap = L.map(containerId, {
        scrollWheelZoom: false
      }).setView(center, zoom);
      instance.map = lMap;

      // CartoDB Voyager tiles
      L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
        maxZoom: 19,
        subdomains: 'abcd',
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/">CARTO</a>'
      }).addTo(lMap);

      // Status indicator
      const badge = document.createElement('div');
      badge.style.cssText = 'position: absolute; bottom: 8px; left: 8px; background: rgba(255,255,255,0.92); border: 1px solid #dfd8ca; padding: 3px 8px; border-radius: 4px; font-size: 10px; font-weight: 600; color: #0F2C2D; z-index: 1000; pointer-events: none; box-shadow: 0 1px 4px rgba(0,0,0,0.1);';
      badge.innerHTML = '🌊 Coastal Map (Offline/Open Resilient)';
      container.appendChild(badge);

      setTimeout(() => {
        lMap.invalidateSize();
      }, 250);

      window.addEventListener('resize', () => {
        lMap.invalidateSize();
      });

      updateLeafletPins(initialPins);
    }

    function updateLeafletPins(pinsData, fitCenter, fitZoom) {
      lMarkers.forEach(m => lMap.removeLayer(m));
      lMarkers = [];

      if (!pinsData || !pinsData.length) return;

      const group = [];

      pinsData.forEach((p, idx) => {
        const isLive = p.is_connected;
        const bgColor = isLive ? '#D9822B' : '#4A6061';
        const rankText = showRankOnPins ? `<span style="font-weight: bold; font-size: 11px; color: #fff;">${idx + 1}</span>` : `<div style="width: 8px; height: 8px; background: #fff; border-radius: 50%; transform: rotate(45deg);"></div>`;

        const icon = L.divIcon({
          className: 'custom-waqt-pin',
          html: `<div style="background: ${bgColor}; border: 2px solid #FFFFFF; border-radius: 50% 50% 50% 0; transform: rotate(-45deg); width: 28px; height: 28px; box-shadow: 0 3px 8px rgba(15,44,45,0.35); display: flex; align-items: center; justify-content: center;">
                   <div style="transform: rotate(45deg); display: flex; align-items: center; justify-content: center;">${rankText}</div>
                 </div>`,
          iconSize: [28, 28],
          iconAnchor: [14, 28],
          popupAnchor: [0, -28]
        });

        const popupContent = buildInfoWindowContent(p, userCoords ? userCoords.lat : null, userCoords ? userCoords.lon : null);
        const marker = L.marker([p.lat, p.lon], { icon }).addTo(lMap).bindPopup(popupContent);

        marker.on('click', () => {
          if (typeof onPinClick === 'function') {
            onPinClick(p, idx);
          }
        });

        lMarkers.push(marker);
        group.push(marker);
      });

      if (fitCenter && fitZoom) {
        lMap.setView(fitCenter, fitZoom);
      } else if (group.length > 1) {
        const featureGroup = L.featureGroup(group);
        lMap.fitBounds(featureGroup.getBounds().pad(0.12));
      } else if (group.length === 1) {
        lMap.setView([pinsData[0].lat, pinsData[0].lon], 14);
      }
    }

    return instance;
  }

  return {
    initMap,
    loadGoogleMapsScript
  };
})();
