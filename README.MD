# BACKEND_MONITORAMENTO – Solar Monitoring API (FastAPI)

This is the backend service for a complete solar plant monitoring platform. Built with FastAPI and PostgreSQL, it provides secure multi-tenant access to real-time solar generation data, performance calculations, API integrations with inverter manufacturers, and PDF report generation.

## Key Features

- JWT-based authentication for users and administrators
- Multi-tenant architecture (each client accesses only their own data)
- Integration with external APIs (Sungrow / iSolarCloud, Deye, Huawei)
- Daily, 7-day, and 30-day performance calculations with per-client caching
- Monthly production targets and dynamic recalculation of performance
- PDF report generation
- Redis-based caching layer
- PostgreSQL persistence with SQLAlchemy
- Admin dashboard routes for managing clients and integrations

## Tech Stack

- Python 3.11
- FastAPI
- PostgreSQL
- SQLAlchemy
- Redis
- Pydantic
- Uvicorn
- Docker / Railway (deployment)
- JWT (authentication)

## Project Structure

backend/
├── app.py # Main FastAPI entry point
├── clients/ # API integrations (Sungrow, Deye, Huawei)
│ ├── isolarcloud_client.py
│ ├── deye_client.py
│ └── huawei_client.py
├── routes/ # API route definitions
│ ├── usinas.py
│ ├── integracoes.py
│ └── auth.py
├── services/ # Business logic (performance, reports, alarms)
├── modelos.py # ORM models (SQLAlchemy)
├── esquemas.py # Pydantic schemas
├── utils.py # Helpers (hashing, auth, timezone)
└── database.py # Database connection

ruby
Copiar
Editar

## Main Endpoints

| Method | Route                                  | Description |
|--------|----------------------------------------|-------------|
| POST   | `/login`                               | Authenticate and return JWT token |
| GET    | `/usina`                               | List plants for the authenticated user |
| GET    | `/geracao_diaria`                      | Retrieve current day's generation |
| GET    | `/performance_30dias`                  | 30-day performance for all plants |
| POST   | `/projecoes/salvar_e_recalcular`       | Save monthly projections and recalculate |
| POST   | `/integracoes/`                        | Save client integration credentials |
| GET    | `/admin/integracoes`                   | (Admin) View and manage platform integrations |

## Environment Variables (`.env.example`)

```env
SECRET_KEY=your_jwt_secret_key
DATABASE_URL=postgresql://user:password@localhost:5432/monitoramento
REDIS_URL=redis://localhost:6379
Running Locally
bash
Copiar
Editar
# Clone the repository
git clone https://github.com/rafamrn/BACKEND_SOLAREYE.git
cd BACKEND_MONITORAMENTO

# Create virtual environment
python -m venv venv
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Start the server
uvicorn app:app --reload
Authentication & Security
Passwords are stored with SHA256 or secure hashing

JWT tokens are used for all protected routes

Admin and client roles are separated

Tokens from integrated platforms (e.g., Sungrow) are stored securely and refreshed automatically when needed

Notes
API responses are optimized with Redis-based caching per user

All integrations use cached tokens and failover handling

Backend is designed to scale per client with independent integration credentials

License
This project is for educational and demonstration purposes only.
If you are interested in contributing or collaborating, feel free to fork or reach out via LinkedIn.