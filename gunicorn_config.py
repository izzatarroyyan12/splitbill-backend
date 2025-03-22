import multiprocessing
import os

# Server socket
bind = f"0.0.0.0:{os.getenv('PORT', '10000')}"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = 'sync'
worker_connections = 1000
timeout = 120
keepalive = 2

# Logging
accesslog = '-'
errorlog = '-'
loglevel = os.getenv('LOG_LEVEL', 'info').lower()
access_log_format = '%({x-real-ip}i)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(L)s'

# Process naming
proc_name = 'livin-backend'

# SSL config
keyfile = os.getenv('SSL_KEY_PATH')
certfile = os.getenv('SSL_CERT_PATH')

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# Limit request line and headers
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190

# Performance tuning
max_requests = 1000
max_requests_jitter = 50
graceful_timeout = 30
keep_alive = 5

# Error handling
capture_output = True
enable_stdio_inheritance = True 