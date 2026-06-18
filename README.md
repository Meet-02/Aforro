# 🛒 Aforro - Retail Inventory Management Backend

This repository contains the backend API for Aforro, a robust retail and inventory management platform built with Django, PostgreSQL, Redis, and Celery.

---

## 🛠️ Setup Instructions (Local Development)

If you prefer to run the application locally without Docker, follow these steps:

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
   * **Terminal 1:** Start the message broker -> `redis-server`
   * **Terminal 2:** Start the API server -> `python manage.py runserver`
   * **Terminal 3:** Start the background worker -> `celery -A config worker --loglevel=info -P solo` *(Note: Omit `-P solo` if running on Mac/Linux)*

---

## 🐳 Docker Usage

The easiest way to run the entire stack (Django API, PostgreSQL Database, Redis Cache, Celery Worker) is using Docker Compose.

1. **Build and start all containers in the background:**
   ```bash
   docker compose up --build -d
   ```

2. **Run database migrations inside the web container:**
   ```bash
   docker compose exec web python manage.py migrate
   ```

3. **Seed the database with test data:**
   ```bash
   docker compose exec web python manage.py seed_groceries
   ```

4. **Monitor the logs in real-time:**
   ```bash
   docker compose logs -f
   ```

5. **Stop and tear down the containers:**
   ```bash
   docker compose down
   ```

---

## 🔌 Sample API Requests

Once the application components are running, you can test the endpoints using standard terminal utilities. 

**CRITICAL NOTE FOR WINDOWS USERS:** When copying these commands, ensure you do not accidentally copy hidden rich-text hyperlinks (like `[http...]`). Only copy the raw text.

### 1. Search for a Product
Retrieves a list of cached products matching a keyword query.
* **cURL (Mac/Linux):**
  ```bash
  curl -X GET "http://127.0.0.1:8000/api/search/products/?q=bread"
  ```
* **PowerShell (Windows):**
  ```powershell
  Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/search/products/?q=bread" -Method GET
  ```

### 2. Get Autocomplete Suggestions
Fast typeahead search matching prefixes. **Note:** Enforces a Redis rate limit of 20 requests per minute per IP.
* **cURL (Mac/Linux):**
  ```bash
  curl -X GET "http://127.0.0.1:8000/api/search/suggest/?q=ban"
  ```
* **PowerShell (Windows):**
  ```powershell
  Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/search/suggest/?q=ban" -Method GET
  ```

### 3. Place a Multi-Item Grocery Order (Checkout)
Submits a checkout payload to a specific store. The entire execution is wrapped inside a database transaction to prevent race conditions.
* **cURL (Mac/Linux):**
  ```bash
  curl -X POST "http://127.0.0.1:8000/orders/"        -H "Content-Type: application/json"        -d '{"store_id": 21, "items": [{"product_id": 1001, "quantity_requested": 5}, {"product_id": 1010, "quantity_requested": 2}]}'
  ```
* **PowerShell (Windows):**
  ```powershell
  Invoke-RestMethod -Uri "http://127.0.0.1:8000/orders/" -Method POST -Headers @{"Content-Type"="application/json"} -Body '{"store_id": 21, "items": [{"product_id": 1001, "quantity_requested": 5}, {"product_id": 1010, "quantity_requested": 2}]}'
  ```

*(Note: When executed, check your active Celery terminal worker to monitor the background processing of the asynchronous order confirmation task.)*

---

---

## ⚡ Notes on Caching & Async Logic

* **Caching (Redis):** Read-heavy endpoints utilize Redis caching. The results of complex search queries are cached for 5 minutes (`timeout=300`), drastically reducing database load.
* **Rate Limiting (Redis):** The Autocomplete API leverages Redis to track IP addresses and enforces a strict rate limit of 20 requests per 60 seconds to prevent abuse.
* **Asynchronous Processing (Celery):** Actions that do not require immediate HTTP responses (like sending Order Confirmations) are offloaded to background workers, ensuring the user receives an instant API response.

---

## 📈 Scalability Considerations

* **Transaction Safety:** Order placement uses `transaction.atomic()` and `select_for_update()`. This enforces row-level database locking, preventing race conditions where multiple concurrent users try to purchase the last item.
* **N+1 Query Prevention:** The Django ORM is optimized using `select_related()` and `prefetch_related()` to ensure related data is fetched in exactly 1 or 2 queries.
