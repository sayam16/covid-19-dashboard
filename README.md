# Scalable COVID-19 Data Analytics Dashboard

Production-oriented full-stack dashboard for COVID-19 monitoring, surge detection, and short-horizon forecasting. The system ingests multiple WHO-aligned datasets, harmonizes country/date series, engineers epidemiological features, and serves interactive analytics through a FastAPI backend and a Next.js frontend.

## Stack

- Backend: FastAPI, Pandas, NumPy, SQLAlchemy, Scikit-learn, XGBoost, TensorFlow/Keras, Statsmodels
- Frontend: Next.js, React, Tailwind CSS, Recharts
- Database: SQLite by default, PostgreSQL-ready through `DATABASE_URL`
- Deployment: Docker, Vercel-friendly frontend, Render or Railway-ready backend

## Python Version

Use Python `3.12` for the backend. The pinned ML stack in this project is not intended for Python `3.14`, and installs may fail by trying to compile packages like `pandas` from source.

## Project Structure

```text
backend/
  app/
    api/routes/
    core/
    db/
    schemas/
    services/
  data/
    raw/
    processed/
    cache/
  models/
  tests/
frontend/
  app/
  components/
  lib/
docker/
  docker-compose.yml
README.md
```

## Features

- Multi-source ingestion from:
  - `WHO-COVID-19-global-daily-data.csv`
  - `WHO-COVID-19-global-data.csv`
  - `WHO-COVID-19-global-hosp-icu-data.csv`
  - `COV_VAC_UPTAKE_2024.csv`
- Data cleaning and harmonization:
  - Country/date normalization
  - Missing-value handling with forward-fill and interpolation
  - Time-series continuity enforcement per country
- Feature engineering:
  - 7-day moving average
  - Week-over-week growth rate
  - 14-day rolling trend delta
  - Surge ratio vs 28-day baseline
- Hybrid forecasting:
  - STL decomposition
  - XGBoost for trend component
  - LSTM for residual component
  - Weighted recombination using `0.4 / 0.4 / 0.2`
- Decision support:
  - Trend classification: `Normal`, `Moderate`, `Surge`
  - AI narrative insights
  - XGBoost feature importance
  - Surge highlighting in charts

## Dataset Setup

Download all four required dataset files and place them in the `backend/data/raw` directory (create the directory if it does not exist).

Expected filenames:

- `WHO-COVID-19-global-daily-data.csv`
- `WHO-COVID-19-global-data.csv`
- `WHO-COVID-19-global-hosp-icu-data.csv`
- `COV_VAC_UPTAKE_2024.csv`

You can also override the paths through:

- `COVID_DAILY_DATA_PATH`
- `COVID_WEEKLY_DATA_PATH`
- `COVID_HOSPITAL_DATA_PATH`
- `COVID_VACCINATION_DATA_PATH`

## Local Setup

### 1. Backend

```bash
cd backend
py -3.12 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Frontend

```bash
cd frontend
npm install
copy .env.example .env.local
npm run dev
```

Frontend default URL: `http://localhost:3000`  
Backend default URL: `http://localhost:8000`

## API Documentation

When the backend is running, interactive docs are available at:

- `http://localhost:8000/docs`

Core endpoints:

- `POST /api/load-data`
  - Loads and preprocesses the datasets
- `GET /api/countries`
  - Returns available country names
- `GET /api/get-country-data?country=India`
  - Returns cleaned country time series and generated insights
- `GET /api/predict?country=India&horizon=14`
  - Returns 7 to 14 day forecast and feature importance
- `GET /api/trend?country=India`
  - Returns `Normal`, `Moderate`, or `Surge`
- `GET /api/global-summary`
  - Returns global totals, trend counts, top surge countries, and global curve data

## Testing

Backend tests:

```bash
cd backend
pytest
```

## Docker

Run both services together:

```bash
cd docker
docker compose up --build
```

## Deployment

### Backend on Render or Railway

- Deploy the `backend/` directory as a Python web service
- Install command: `pip install -r requirements.txt`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Set the dataset path environment variables or mount the raw CSV files
- For PostgreSQL, replace `DATABASE_URL` with your hosted connection string

### Frontend on Vercel

- Deploy the `frontend/` directory
- Set `NEXT_PUBLIC_API_BASE_URL` to your deployed backend URL, for example `https://your-api.onrender.com/api`
- Build command: `npm run build`

## Notes

- The backend caches the merged dataset in [backend/data/processed](/C:/Users/mohit/Documents/project/backend/data/processed) for faster reloads.
- Forecast endpoints require the ML dependencies listed in `backend/requirements.txt`.
- SQLite is the default database to keep local setup simple; the SQLAlchemy configuration supports PostgreSQL through `DATABASE_URL`.
