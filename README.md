# Waqt (वेळ) — Coastal Restaurant Capacity & Queue Platform

**Waqt** is a live restaurant capacity and queue-management platform designed specifically around the Palghar–Virar coastal belt and Koli/Maharashtrian coastal food culture. 

Unlike standard discovery apps, Waqt solves the real-world operational problem of **wait-time transparency** and **floor management** for heavily trafficked coastal eateries. It bridges the gap between eager diners and busy restaurant hosts.

![Waqt Hero](static/images/coastal-hero.jpg)

## 🌊 Core Features

### 1. Honest Directory vs. Live Partners
- **Passive Directory:** A beautifully mapped directory of verified restaurants along the Virar to Dahanu coastline.
- **Live Partners:** Verified restaurant owners can "Claim" their listing. Once approved, they gain access to live capacity tracking and digital queueing. 
- *Honesty Barrier:* The system mathematically rejects any reservation or queue attempt for a passive directory listing, prompting users to ask the owner to join Waqt.

### 2. Live Floor Allocation Algorithm
- A **Greedy Table Allocation Engine** dynamically maps party sizes to the most efficient physical tables (e.g., placing a party of 3 at a 4-seater, but not at a 6-seater unless necessary).
- Owners update table statuses (Available, Occupied, Reserved, Cleaning) in real-time via their digital Floor Console.

### 3. Dynamic FIFO Queue System
- Live calculation of **Estimated Wait Times (EWT)** based on live turnover rates and queue depth.
- Diners receive a digital Ticket Number and wait-time metric.

### 4. Haversine Geodesic Fencing
- The platform uses geographic coordinate math to ensure diners can only join a live queue if they are genuinely within driving distance of the restaurant.

### 5. Bespoke Coastal UI/UX
- Custom styling utilizing Palghar-coast color palettes: *Deep Tide, Sand, Driftwood, Turmeric, Chilli*.
- Interactive dual-pin Leaflet mapping rendering raw GeoJSON injects directly from the backend.
- Marathi typography integrations.

## 🛠 Tech Stack

- **Backend:** Django 5.x (Python)
- **Database:** SQLite (Development)
- **Frontend:** HTML5, CSS3, Vanilla JavaScript
- **Mapping:** Leaflet.js (Interactive mapping)
- **Architecture:** Monolithic MVC (Model-View-Template) with RESTful API endpoints for asynchronous map/queue updates.

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Git

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/shrawani3007/Waqt.git
   cd Waqt
   ```

2. **Set up a Virtual Environment:**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run Migrations:**
   ```bash
   python manage.py migrate
   ```

5. **Load Verified Coastal Restaurant Data:**
   ```bash
   python manage.py import_restaurants scratch/coastal_verified.json
   ```

6. **Start the Development Server:**
   ```bash
   python manage.py runserver
   ```

7. **Access the App:**
   Open your browser and navigate to `http://127.0.0.1:8000/`.

## 🧪 Testing

The platform includes a robust suite of E2E and integration tests verifying geographic restrictions, capacity math, and directory separation.

```bash
python manage.py test core
```

## 👥 Roles & Workflows

1. **Diners:** Register, explore the coastal map, view live capacities, and join queues.
2. **Owners:** Claim a directory listing (requires FSSAI/GSTIN), access the Floor Console, and manage table turnover.
3. **Admins:** Approve claims to transition restaurants from passive listings to live partners.

---
*Built as a Capstone Project bridging hospitality intelligence with Maharashtrian coastal culture.*
