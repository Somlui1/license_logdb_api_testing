# License LogDB API & SOS SLA Calculator

FastAPI backend service for license log management, WatchGuard patch tracking, and **SOS SLA Calculation with Caching**.

---

## 📐 Architecture Overview

```
📁 app/
├── main.py                  # App entrypoint & router registration
├── server.py                # Uvicorn server config
├── .env                     # Environment variables
├── db/                      # Database Models (SQLAlchemy ORM)
│   ├── SOS_holiday.py       # Holiday model (holidays table)
│   ├── SOS_sla_cache.py     # [NEW] SLA cache model (sos_sla_cache table)
│   ├── license_logsdb.py    # License log models
│   ├── server_logsdb.py     # Server log models
│   └── watchguarddb.py      # WatchGuard patch models
├── routers/                 # API Endpoints (FastAPI Routers)
│   ├── SOS.py               # SOS endpoints (ticket, holidays, SLA)
│   ├── server_logs.py       # Server log endpoints
│   ├── testing.py           # License testing endpoints
│   ├── thai_karaoke.py      # Thai romanization
│   └── watchguard.py        # WatchGuard endpoints
├── service/                 # Business Logic (Service Layer)
│   ├── SOS_fn.py            # Intranet ticket submission
│   ├── SOS_sla.py           # [NEW] SLA calculator service
│   ├── GLPI.py              # GLPI integration
│   └── watchguard_fn.py     # WatchGuard logic
├── schema/                  # Pydantic Validation Models
│   ├── SOS_sla_validate.py  # [NEW] SLA request/response schemas
│   ├── license_log_validate.py
│   ├── server_logs_validate.py
│   └── watchguard_validate.py
└── test/                    # Standalone Test Scripts
    ├── SOS_sla_test.py      # [NEW] SLA test
    ├── SOS_test.py          # SOS ticket test
    └── sync_holidays.py     # Holiday sync script
```

---

## 🎯 SOS SLA Feature — Implementation Plan

### Goal

Calculate if a ticket met the SLA (**Accepted within 8 working hours**).
Results are cached in PostgreSQL for instant re-lookups.

### Business Rules

| Rule | Detail |
|---|---|
| Workday | 08:00 – 17:00 (9 hrs gross) |
| Break | 12:00 – 13:00 (excluded) |
| Net working mins/day | **480 min** (8 hrs) |
| SLA threshold | **480 working minutes** (8 working hours) |
| Sunday | Always off |
| Saturday & Holidays | Checked against `holidays` table in DB |

### Key Data Fields (from Express.js Microservice)

| Field | Purpose | Format |
|---|---|---|
| `REQ_NO` | Ticket ID (cache key) | `76488` |
| `REQ_DATE` | Ticket created | `"dd-MM-yyyy HH:mm"` |
| `ACEPT_DATE` | Ticket accepted | `"yyyy-MM-dd HH:mm:ss"` |
| `IT_EMPNO` | IT staff ID (query param) | `"10002898"` |

---

## 🔄 Data Flow

```mermaid
sequenceDiagram
    participant Client
    participant FastAPI as FastAPI (/SOS/sla)
    participant Express as Express.js (localhost:3434)
    participant DB as PostgreSQL (SOS DB)

    Client->>FastAPI: GET /SOS/sla/calculate?id=10002898&year=2026
    FastAPI->>DB: Check sos_sla_cache for each ticket
    alt Cache HIT
        DB-->>FastAPI: cached SLA result
        FastAPI-->>Client: SLA result (from_cache: true)
    else Cache MISS
        FastAPI->>Express: GET /sos/log?id={id}&year={year}&$count=true
        Express-->>FastAPI: ticket data array
        FastAPI->>DB: Query holidays table
        DB-->>FastAPI: holiday dates set
        FastAPI->>FastAPI: Calculate working minutes per ticket
        FastAPI-->>Client: SLA results (from_cache: false)
        FastAPI->>DB: BackgroundTask → save to sos_sla_cache
    end
```

---

## 🗄️ Database Flow

```mermaid
erDiagram
    SOS_DATABASE {
        string name "PostgreSQL: SOS @ 10.10.3.215:5432"
    }

    holidays {
        int id PK
        date date UK "Holiday date (unique)"
        string name "Holiday name"
        datetime created_at "Auto timestamp"
    }

    sos_sla_cache {
        int id PK
        string ticket_id UK "REQ_NO (unique)"
        string it_empno "IT staff employee number"
        datetime created_at_ticket "REQ_DATE parsed"
        datetime accepted_at "ACEPT_DATE parsed"
        int working_minutes "Business minutes calculated"
        boolean sla_met "true if <= 480 min"
        datetime cached_at "Auto timestamp"
    }

    SOS_DATABASE ||--o{ holidays : contains
    SOS_DATABASE ||--o{ sos_sla_cache : contains
    sos_sla_cache }o--o{ holidays : "checks against"
```

---

## 🔗 API Endpoints (SOS SLA)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/SOS/sla/calculate?id={empno}&year={year}` | Fetch tickets from Express.js, calculate SLA, return results |
| `GET` | `/SOS/sla/cache?start_date=&end_date=` | Query cached SLA results by date range |

### Example Request

```
GET http://localhost:8000/SOS/sla/calculate?id=10002898&year=2026
```

### Example Response

```json
{
  "total_tickets": 15,
  "sla_met_count": 12,
  "sla_missed_count": 3,
  "results": [
    {
      "ticket_id": "76488",
      "req_user": "Monton Sirithai",
      "req_date": "2026-01-05T08:29:00",
      "acept_date": "2026-01-05T08:37:28",
      "working_minutes": 8,
      "sla_met": true,
      "from_cache": false
    }
  ]
}
```

---

## 🧮 SLA Calculation Logic

```mermaid
flowchart TD
    A["Receive ticket data"] --> B{"ACEPT_DATE exists?"}
    B -- No --> Z["Skip — not yet accepted"]
    B -- Yes --> C["Parse REQ_DATE & ACEPT_DATE"]
    C --> D["Start = REQ_DATE, End = ACEPT_DATE"]
    D --> E{"Same day?"}
    E -- Yes --> F["Clamp to 08:00-17:00\nSubtract break overlap\nReturn minutes"]
    E -- No --> G["Day-by-day loop"]
    G --> H{"Is working day?"}
    H -- "Sunday" --> I["Skip day"]
    H -- "Saturday → check holidays DB" --> J{"In holidays?"}
    J -- Yes --> I
    J -- No --> K["Count as working day"]
    H -- "Weekday" --> L{"In holidays?"}
    L -- Yes --> I
    L -- No --> K
    K --> M["Clamp hours 08:00-17:00\nSubtract 12:00-13:00 break\nAdd minutes to total"]
    M --> N{"More days?"}
    N -- Yes --> H
    N -- No --> O["Total working minutes"]
    O --> P{"<= 480 min?"}
    P -- Yes --> Q["✅ SLA Met"]
    P -- No --> R["❌ SLA Missed"]
```

---

## ⚙️ Configuration (.env)

```env
## Express.js Microservice
SOS_MICROSERVICE_URL=http://localhost:3434

## SOS Database
SOS_DB_URL=postgresql://itsupport:aapico@10.10.3.215:5432/SOS

## SOS Intranet credentials
SOSusername=itsupport
SOSpassword=support
```

---

## 🚀 Quick Start

```bash
# Start with Docker
docker-compose up --build

# Or run locally
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Test SLA calculation
curl "http://localhost:8000/SOS/sla/calculate?id=10002898&year=2026"
```

---

## 🧪 Test Scripts

```bash
# Sync holidays from external API
python -m app.test.sync_holidays

# Test SOS ticket submission
python -m app.test.SOS_test

# Test SLA calculation
python -m app.test.SOS_sla_test
```
