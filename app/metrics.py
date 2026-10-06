from prometheus_client import Counter

REQUESTS = Counter("http_requests_total", "Total HTTP requests", ["method", "path", "status"])
TICKETS_CREATED = Counter("tickets_created_total", "Tickets created", ["category", "priority"])
