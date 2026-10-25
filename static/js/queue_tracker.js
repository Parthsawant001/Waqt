// Live Queue Tracker with Web Notification API and Polling
class QueueTracker {
  constructor(ticketId, pollIntervalMs = 12000) {
    this.ticketId = ticketId;
    this.pollIntervalMs = pollIntervalMs;
    this.timer = null;
    this.notificationAudio = new Audio('https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3');
    this.initNotifications();
    this.startPolling();
  }

  initNotifications() {
    if ('Notification' in window && Notification.permission === 'default') {
      const banner = document.getElementById('notification-permission-prompt');
      if (banner) {
        banner.style.display = 'block';
        const btn = document.getElementById('enable-notifications-btn');
        if (btn) {
          btn.addEventListener('click', () => {
            Notification.requestPermission().then(permission => {
              if (permission === 'granted') {
                banner.style.display = 'none';
              }
            });
          });
        }
      }
    }
  }

  notifyCustomer(statusData) {
    // 1. Browser Push Notification
    if ('Notification' in window && Notification.permission === 'granted') {
      try {
        new Notification("Your Table is Ready! — Waqt", {
          body: "Please proceed to the restaurant host stand right away.",
          icon: '/static/icons/table.svg',
          requireInteraction: true
        });
      } catch (e) {
        console.warn("Notification error:", e);
      }
    }

    // 2. Play subtle chime
    try {
      this.notificationAudio.play().catch(() => {});
    } catch(e) {}

    // 3. Update in-app banner
    const calledBanner = document.getElementById('called-banner');
    if (calledBanner) {
      calledBanner.style.display = 'block';
    }
  }

  async poll() {
    try {
      const resp = await fetch(`/queue/api/${this.ticketId}/status/`);
      if (!resp.ok) return;
      const data = await resp.json();

      // Update DOM
      const posEl = document.getElementById('queue-position');
      const waitEl = document.getElementById('queue-wait');
      const aheadEl = document.getElementById('parties-ahead');
      const statusBadge = document.getElementById('queue-status-badge');

      if (posEl) posEl.textContent = `#${data.position}`;
      if (waitEl) waitEl.textContent = `${data.estimated_wait_minutes} min`;
      if (aheadEl) aheadEl.textContent = data.parties_ahead;

      if (statusBadge) {
        statusBadge.textContent = data.status_display;
        if (data.status === 'CALLED') {
          statusBadge.className = 'badge-status badge-called';
        } else if (data.status === 'SEATED') {
          statusBadge.className = 'badge-status badge-available';
        }
      }

      if (data.is_called) {
        this.notifyCustomer(data);
        clearInterval(this.timer);
      } else if (!data.is_active) {
        clearInterval(this.timer);
      }
    } catch (err) {
      console.warn("Queue polling error:", err);
    }
  }

  startPolling() {
    this.poll();
    this.timer = setInterval(() => this.poll(), this.pollIntervalMs);
  }
}
