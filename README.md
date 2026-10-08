# King Cafe – Digital Ordering & Management System

A complete, modern, web-based digital café ordering and management system designed to transition traditional offline cafés into a seamless, QR-based digital ordering workflow.

## 🚀 Features

### Customer Experience
*   **QR-Based Table Detection:** Scan a QR code on the table to securely load the digital menu for that specific table.
*   **Digital Menu:** Browse available food items, filter by category, and see Veg/Non-Veg indicators.
*   **Live Cart & Checkout:** Manage orders dynamically via secure backend sessions.
*   **Order Tracking:** Monitor order status in real-time.
*   **AI Assistant:** A smart chat assistant that recommends food based on the *actual* active menu.

### Admin Authority
*   **Complete Menu Control (CRUD):** Add, edit, or toggle the availability of food items.
*   **Data Integrity:** Delete operations utilize an Archive/Soft-delete mechanism so historical bills and orders are never broken.
*   **Order Verification:** Review incoming orders from customers before dispatching them to the kitchen.
*   **Table Management:** Generate and print physical QR codes for tables.
*   **Billing & Payments:** Generate print-ready receipts and manage payment states (Pending, Paid, Failed, Refunded).
*   **Live Analytics:** Monitor daily sales, active customers, and queue volumes.

### Kitchen (Chef) Workflow
*   **Live Order Board:** Real-time visibility into accepted orders.
*   **Streamlined Actions:** Start preparation and mark orders as "Ready", instantly notifying the Admin.

## 🛠️ Technology Stack
*   **Backend:** Python, Flask, Flask-Blueprints, Flask-Session
*   **Database:** MySQL, SQLAlchemy (ORM)
*   **Security:** Bcrypt (Password Hashing), Secure Sessions
*   **Frontend:** HTML5, CSS3 (Modern Vanilla), JavaScript (Fetch API)
*   **Integrations:** Google Generative AI (Gemini), `qrcode` library

## 📋 Requirements
*   Python 3.8+
*   MySQL Server 8.0+

## ⚙️ Installation & Setup

1. **Clone & Environment Setup:**
   ```bash
   git clone <repository-url>
   cd "cafe project"
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   pip install -r requirements.txt
   ```

2. **Database Configuration (MySQL):**
   Ensure MySQL is running and create the database:
   ```sql
   CREATE DATABASE smart_cafe;
   ```

3. **Environment Variables:**
   Rename `.env.example` to `.env` and configure your credentials:
   ```env
   SECRET_KEY=your_super_secret_key
   DATABASE_URL=mysql+pymysql://root:password@localhost/smart_cafe
   FLASK_DEBUG=True
   AI_API_KEY=your_gemini_api_key
   ```

4. **Initialize the Database:**
   The database schema is automatically generated when the app runs for the first time.

5. **Create the Initial Admin Account:**
   Do NOT hardcode admin passwords! Use the secure interactive CLI tool provided:
   ```bash
   python init_admin.py
   ```

6. **Run the Application (Development):**
   ```bash
   python run.py
   ```
   The application will be available at `http://localhost:5000`.

## 🌐 Deployment Ready (Production)

Do **not** use the Flask development server (`run.py`) in production.

1. Set `FLASK_DEBUG=False` in your `.env` file.
2. Use a production WSGI server like **Gunicorn**:
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:8000 wsgi:app
   ```
3. Use a reverse proxy like **Nginx** to serve static files and forward traffic to Gunicorn.

## 🧪 Testing Notes
*   **Authentication:** Ensure roles restrict access appropriately (Customer cannot see Admin dashboards).
*   **Pricing Integrity:** The frontend cart only sends item IDs to the backend. The backend reconstructs the grand total securely using MySQL prices.
*   **Menu Archival:** Try archiving a food item. It will disappear from the customer menu but remain intact on past generated bills.
