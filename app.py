from fastapi import FastAPI, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from collections import defaultdict
import time
import uuid

EMAIL = "24ds3000047@ds.study.iitm.ac.in"

app = FastAPI(title="Q9 Orders API")


@app.get("/")
def root():
    return {"status": "running"}


# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

TOTAL_ORDERS = 45
RATE_LIMIT = 16
WINDOW = 10  # seconds

# In-memory stores
idempotency_store = {}
client_requests = defaultdict(list)

# Fixed catalog
catalog = [
    {"id": i, "item": f"Order-{i}"}
    for i in range(1, TOTAL_ORDERS + 1)
]


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    client = request.headers.get("X-Client-Id", "anonymous")
    now = time.time()

    # Keep only requests in the last WINDOW seconds
    client_requests[client] = [
        t for t in client_requests[client]
        if now - t < WINDOW
    ]

    # Reject after RATE_LIMIT requests
    if len(client_requests[client]) >= RATE_LIMIT:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"},
            headers={"Retry-After": str(WINDOW)},
        )

    client_requests[client].append(now)

    response = await call_next(request)
    return response


@app.post("/orders", status_code=201)
def create_order(idempotency_key: str = Header(alias="Idempotency-Key")):
    if idempotency_key in idempotency_store:
        return idempotency_store[idempotency_key]

    order = {
        "id": str(uuid.uuid4()),
        "email": EMAIL
    }

    idempotency_store[idempotency_key] = order
    return order


@app.get("/orders")
def list_orders(limit: int = 10, cursor: str | None = None):
    start = int(cursor) if cursor else 0
    end = min(start + limit, TOTAL_ORDERS)

    items = catalog[start:end]

    next_cursor = str(end) if end < TOTAL_ORDERS else None

    return {
        "items": items,
        "next_cursor": next_cursor
    }