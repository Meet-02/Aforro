# 🛒 Aforro - Retail Inventory Management Backend

This repository contains the backend API for Aforro, a robust retail and inventory management platform built with Django, PostgreSQL, Redis, and Celery.

---

## 🛠️ Setup Instructions (Local Development)

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd Aforro
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\Activate.ps1
   # On Mac/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Apply database migrations:**
   ```bash
   python manage.py migrate
   ```

5. **Seed the database with initial grocery data:**
   ```bash
   python manage.py seed_groceries
   ```

6. **Start the application components (requires 3 terminal windows):**
   * **Terminal 1:** Start the message broker → `redis-server`
   * **Terminal 2:** Start the API server → `python manage.py runserver`
   * **Terminal 3:** Start the background worker → `celery -A config worker --loglevel=info -P solo` *(Omit `-P solo` on Mac/Linux)*

---

## 🐳 Docker Usage

The easiest way to run the entire stack (Django API, PostgreSQL, Redis, Celery Worker) is using Docker Compose.

> **Before starting:** Open `config/settings.py` and make sure `ALLOWED_HOSTS = ['*']`. Without this, Django rejects all requests arriving at `0.0.0.0:8000`.

1. **Build and start all containers:**
   ```bash
   docker compose up --build -d
   ```

2. **Seed the database with test data:**
   ```bash
   docker compose exec web python manage.py seed_groceries
   ```
   *(Migrations run automatically when the container starts — no need to run them manually.)*

3. **Monitor the logs in real-time:**
   ```bash
   docker compose logs -f
   ```

4. **Stop and tear down the containers:**
   ```bash
   docker compose down
   ```

---

## 📖 API Documentation (Swagger & ReDoc)

Once the server is running, interactive API docs are available at:

| URL | Description |
|---|---|
| `http://127.0.0.1:8000/api/docs/` | **Swagger UI** — interactive, try endpoints live |
| `http://127.0.0.1:8000/api/redoc/` | **ReDoc** — clean, readable reference |

All endpoints, parameters, and response shapes are fully documented and testable directly from the browser — no curl or Postman needed.

---

## 🔌 Sample API Requests

> **IDs note:** `seed_groceries` creates **store ID `1`** and products with **IDs starting from `1`**. Use those in the requests below.

### 1. Search for a Product
* **cURL (Mac/Linux):**
  ```bash
  curl -X GET "http://127.0.0.1:8000/api/search/products/?q=bread"
  ```
* **PowerShell (Windows):**
  ```powershell
  Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/search/products/?q=bread" -Method GET
  ```

### 2. Get Autocomplete Suggestions
Rate-limited to 20 requests per minute per IP. Requires minimum 3 characters.
* **cURL (Mac/Linux):**
  ```bash
  curl -X GET "http://127.0.0.1:8000/api/search/suggest/?q=ban"
  ```
* **PowerShell (Windows):**
  ```powershell
  Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/search/suggest/?q=ban" -Method GET
  ```

### 3. Place an Order
* **cURL (Mac/Linux):**
  ```bash
  curl -X POST "http://127.0.0.1:8000/orders/" \
       -H "Content-Type: application/json" \
       -d '{"store_id": 1, "items": [{"product_id": 1, "quantity_requested": 2}, {"product_id": 2, "quantity_requested": 1}]}'
  ```
* **PowerShell (Windows):**
  ```powershell
  Invoke-RestMethod -Uri "http://127.0.0.1:8000/orders/" -Method POST -Headers @{"Content-Type"="application/json"} -Body '{"store_id": 1, "items": [{"product_id": 1, "quantity_requested": 2}, {"product_id": 2, "quantity_requested": 1}]}'
  ```

*(After placing an order, check your Celery terminal to see the async order confirmation task fire.)*

### 4. List Orders for a Store
* **cURL (Mac/Linux):**
  ```bash
  curl -X GET "http://127.0.0.1:8000/stores/1/orders/"
  ```

### 5. List Inventory for a Store
* **cURL (Mac/Linux):**
  ```bash
  curl -X GET "http://127.0.0.1:8000/stores/1/inventory/"
  ```

---

## ⚡ Notes on Caching & Async Logic

* **Caching (Redis):** The Product Search API (`/api/search/products/`) caches results in Redis for 5 minutes (`timeout=300`), reducing database load for repeated searches.
* **Rate Limiting (Redis):** The Autocomplete API (`/api/search/suggest/`) enforces a limit of 20 requests per 60 seconds per IP using a Redis atomic counter.
* **Asynchronous Processing (Celery):** After an order is saved, an async Celery task fires for the confirmation notification — keeping the API response instant. The task is dispatched **after** `transaction.atomic()` closes to ensure the order is committed before the worker reads it.

---

## 📈 Scalability Considerations

* **Transaction Safety:** Order placement uses `transaction.atomic()` and `select_for_update()`, enforcing row-level locking to prevent race conditions when multiple users purchase the same item simultaneously.
* **N+1 Query Prevention:** All list endpoints use `select_related()`, `prefetch_related()`, and `annotate()` to fetch related data in 1–2 SQL queries regardless of result size.
* **Stateless Web Nodes:** The Django API holds no in-process state, so multiple instances can run behind a load balancer without any code changes.
* **Celery Worker Scaling:** Workers are stateless — run `docker compose up --scale celery=4` to add more workers during high-volume periods.