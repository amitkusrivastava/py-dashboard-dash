worker_class = "uvicorn_worker.UvicornWorker"
workers = 2  # tune via load tests
bind = "0.0.0.0:8000"
timeout = 60
graceful_timeout = 30
keepalive = 5
forwarded_allow_ips = "10.0.0.0/8,127.0.0.1"

# hygiene
max_requests = 2000
max_requests_jitter = 200

# security limits
limit_request_fields = 100
limit_request_field_size = 8190   # adjust prudently
# limit_request_line = 4094       # enable when needed
