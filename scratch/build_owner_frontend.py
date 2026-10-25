import os

dashboard_html = """{% extends 'base.html' %}
{% load static waqt_tags %}

{% block title %}Owner Operations Center ?" {{ restaurant.name }}{% endblock %}

{% block content %}
<div class="waqt-container-wide" style="padding: 36px 24px;">
  <!-- Owner Header -->
  <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: var(--border-subtle); padding-bottom: 20px; margin-bottom: 28px;">
    <div>
      <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">
        <span class="pilot-tag" style="background: var(--turmeric); color: #fff; border: none;">Operations Dashboard</span>
        <span class="marathi-accent" style="font-size: 18px;">{{ restaurant.locality }}</span>
      </div>
      <h1 style="font-size: 32px; margin: 0;">{{ restaurant.name }}</h1>
    </div>

    <!-- Quick Navigation Bar -->
    <div style="display: flex; gap: 10px; flex-wrap: wrap;">
      <a href="{% url 'owner_dashboard' %}" class="btn btn-primary btn-sm">Live Floor</a>
      <a href="{% url 'owner_tables' %}" class="btn btn-outline btn-sm">Tables</a>
      <a href="{% url 'owner_queue' %}" class="btn btn-outline btn-sm">Queue</a>
      <a href="{% url 'owner_reservations' %}" class="btn btn-outline btn-sm">Reservations</a>
      <a href="{% url 'owner_menu' %}" class="btn btn-outline btn-sm">Menu</a>
      <a href="#" class="btn btn-accent btn-sm">Kitchen Display</a>
      <a href="{% url 'owner_analytics' %}" class="btn btn-outline btn-sm">Analytics</a>
    </div>
  </div>

  <!-- Live Metrics Ribbon -->
  <div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 16px; margin-bottom: 32px;" id="dashboard-metrics">
    <div style="background: #fff; border: var(--border-subtle); border-radius: var(--radius-md); padding: 20px; text-align: center;">
      <div style="font-size: 11px; text-transform: uppercase; color: var(--driftwood); font-weight: 600;">Available Tables</div>
      <div id="metric-available-tables" style="font-size: 32px; font-weight: 700; color: var(--status-available);">--</div>
    </div>
    <div style="background: #fff; border: var(--border-subtle); border-radius: var(--radius-md); padding: 20px; text-align: center;">
      <div style="font-size: 11px; text-transform: uppercase; color: var(--driftwood); font-weight: 600;">Occupied Tables</div>
      <div id="metric-occupied-tables" style="font-size: 32px; font-weight: 700; color: var(--status-occupied);">--</div>
    </div>
    <div style="background: #fff; border: var(--border-subtle); border-radius: var(--radius-md); padding: 20px; text-align: center;">
      <div style="font-size: 11px; text-transform: uppercase; color: var(--driftwood); font-weight: 600;">Active Queue</div>
      <div id="metric-active-queue" style="font-size: 32px; font-weight: 700; color: var(--turmeric);">--</div>
    </div>
    <div style="background: #fff; border: var(--border-subtle); border-radius: var(--radius-md); padding: 20px; text-align: center;">
      <div style="font-size: 11px; text-transform: uppercase; color: var(--driftwood); font-weight: 600;">Today's Checked-in</div>
      <div id="metric-checked-in" style="font-size: 32px; font-weight: 700; color: var(--deep-tide);">--</div>
    </div>
    <div style="background: #fff; border: var(--border-subtle); border-radius: var(--radius-md); padding: 20px; text-align: center;">
      <div style="font-size: 11px; text-transform: uppercase; color: var(--driftwood); font-weight: 600;">Kitchen Pending</div>
      <div id="metric-kitchen-pending" style="font-size: 32px; font-weight: 700; color: var(--chilli);">--</div>
    </div>
  </div>

  <div style="display: grid; grid-template-columns: 1.4fr 0.8fr; gap: 32px;">
    <!-- Live Floor Grid -->
    <div style="background: #fff; border: var(--border-subtle); border-radius: var(--radius-md); padding: 28px; box-shadow: var(--shadow-subtle);">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
        <h2 style="font-size: 22px; margin: 0;">Live Dining Floor State</h2>
      </div>
      <div class="floor-grid" id="floor-grid-container" style="grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));">
        <!-- JS Injected Tables -->
      </div>
    </div>

    <!-- Live Queue & Upcoming Reservations -->
    <div>
      <!-- Queue -->
      <div style="background: #fff; border: var(--border-subtle); border-radius: var(--radius-md); padding: 24px; margin-bottom: 24px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
          <h3 style="font-size: 18px; margin: 0;">Active Queue (FIFO)</h3>
        </div>
        <div id="queue-container" style="display: flex; flex-direction: column; gap: 10px;">
          <!-- JS Injected -->
        </div>
      </div>

      <!-- Kitchen -->
      <div style="background: #fff; border: var(--border-subtle); border-radius: var(--radius-md); padding: 24px; margin-bottom: 24px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
          <h3 style="font-size: 18px; margin: 0;">Active Kitchen Orders</h3>
        </div>
        <div id="kitchen-container" style="display: flex; flex-direction: column; gap: 10px;">
          <!-- JS Injected -->
        </div>
      </div>
    </div>
  </div>
</div>
{% endblock %}

{% block extra_js %}
<script src="{% static 'js/owner_operations.js' %}"></script>
{% endblock %}
"""

js_code = """
// Owner Operations Polling Logic

let dashboardPollingInterval;

function fetchDashboardData() {
    if (document.visibilityState !== 'visible') return;

    fetch('/api/owner/dashboard/')
        .then(res => {
            if (!res.ok) throw new Error('API error');
            return res.json();
        })
        .then(data => {
            updateMetrics(data.metrics);
            updateTables(data.tables);
            updateQueue(data.queue);
            updateKitchen(data.kitchen_orders);
        })
        .catch(err => console.error("Error fetching dashboard data:", err));
}

function updateMetrics(metrics) {
    document.getElementById('metric-available-tables').innerText = metrics.available_tables;
    document.getElementById('metric-occupied-tables').innerText = metrics.occupied_tables;
    document.getElementById('metric-active-queue').innerText = metrics.waiting_queue;
    document.getElementById('metric-checked-in').innerText = metrics.checked_in + " / " + metrics.total_reservations;
    document.getElementById('metric-kitchen-pending').innerText = metrics.kitchen_pending;
}

function updateTables(tables) {
    const container = document.getElementById('floor-grid-container');
    if (!container) return;
    
    container.innerHTML = '';
    tables.forEach(t => {
        const div = document.createElement('div');
        div.className = `table-cell status-${t.status.toLowerCase()}`;
        div.innerHTML = `
            <div class="table-number">T${t.table_number}</div>
            <div class="table-capacity">${t.capacity} Persons</div>
            <span class="badge-status badge-${t.status.toLowerCase()}" style="font-size: 10px; padding: 2px 6px;">${t.status}</span>
            <div style="margin-top: 10px;">
                <select class="form-select form-select-sm status-dropdown" data-id="${t.id}" style="font-size: 11px; padding: 2px;">
                    <option value="AVAILABLE" ${t.status === 'AVAILABLE' ? 'selected' : ''}>Available</option>
                    <option value="OCCUPIED" ${t.status === 'OCCUPIED' ? 'selected' : ''}>Occupied</option>
                    <option value="RESERVED" ${t.status === 'RESERVED' ? 'selected' : ''}>Reserved</option>
                    <option value="CLEANING" ${t.status === 'CLEANING' ? 'selected' : ''}>Cleaning</option>
                    <option value="OUT_OF_SERVICE" ${t.status === 'OUT_OF_SERVICE' ? 'selected' : ''}>Out of Service</option>
                </select>
            </div>
        `;
        container.appendChild(div);
    });

    // Attach listeners
    document.querySelectorAll('.status-dropdown').forEach(sel => {
        sel.addEventListener('change', (e) => {
            const tableId = e.target.dataset.id;
            const newStatus = e.target.value;
            fetch(`/api/owner/tables/${tableId}/status/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({ status: newStatus })
            }).then(res => res.json()).then(res => {
                if(res.status === 'success') fetchDashboardData();
            });
        });
    });
}

function updateQueue(queue) {
    const container = document.getElementById('queue-container');
    if (!container) return;
    
    container.innerHTML = '';
    if (queue.length === 0) {
        container.innerHTML = '<p style="font-size: 13px; color: var(--wet-sand); margin: 0;">Queue is empty.</p>';
        return;
    }
    
    queue.forEach(q => {
        container.innerHTML += `
            <div style="background: var(--shell); border: var(--border-subtle); padding: 12px; border-radius: var(--radius-sm); display: flex; justify-content: space-between; align-items: center;">
                <div>
                  <strong style="font-size: 14px;">#${q.position} • ${q.customer_name}</strong>
                  <div style="font-size: 12px; color: var(--driftwood);">Party of ${q.party_size} • Est: ${q.estimated_wait_minutes}m</div>
                </div>
                <div>
                  <button class="btn btn-accent btn-sm" onclick="callQueue(${q.id})">CALL</button>
                </div>
            </div>
        `;
    });
}

function updateKitchen(orders) {
    const container = document.getElementById('kitchen-container');
    if (!container) return;
    
    container.innerHTML = '';
    if (orders.length === 0) {
        container.innerHTML = '<p style="font-size: 13px; color: var(--wet-sand); margin: 0;">No active kitchen orders.</p>';
        return;
    }
    
    orders.forEach(o => {
        container.innerHTML += `
            <div style="background: var(--shell); border: var(--border-subtle); padding: 12px; border-radius: var(--radius-sm); font-size: 13px;">
                <div style="display: flex; justify-content: space-between;">
                  <strong>Order #${o.order_number} (T${o.table_number})</strong>
                  <span class="badge-status badge-${o.status.toLowerCase()}" style="font-size: 10px;">${o.status}</span>
                </div>
                <div style="color: var(--wet-sand); margin-top: 4px;">${o.items.length} items</div>
            </div>
        `;
    });
}

function callQueue(id) {
    fetch(`/api/owner/queue/${id}/call/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        }
    }).then(res => res.json()).then(() => fetchDashboardData());
}

document.addEventListener('DOMContentLoaded', () => {
    fetchDashboardData();
    // Poll every 12 seconds
    dashboardPollingInterval = setInterval(fetchDashboardData, 12000);
    
    // Pause polling when tab is hidden
    document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'visible') {
            fetchDashboardData();
            dashboardPollingInterval = setInterval(fetchDashboardData, 12000);
        } else {
            clearInterval(dashboardPollingInterval);
        }
    });
});
"""

with open('templates/owner/dashboard.html', 'w', encoding='utf-8') as f:
    f.write(dashboard_html)

with open('static/js/owner_operations.js', 'w', encoding='utf-8') as f:
    f.write(js_code)

print("Owner dashboard frontend built.")
