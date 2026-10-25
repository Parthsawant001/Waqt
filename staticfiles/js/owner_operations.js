// Owner Operations Polling Logic

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

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
