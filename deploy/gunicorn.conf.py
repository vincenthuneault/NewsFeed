# Gunicorn — configuration production
import multiprocessing

bind = "127.0.0.1:5000"
workers = min(4, multiprocessing.cpu_count() * 2 + 1)
worker_class = "sync"
timeout = 120
keepalive = 5
max_requests = 1000
max_requests_jitter = 100

# Logging
accesslog = "/home/vhds/NewsFeed/logs/gunicorn_access.log"
errorlog  = "/home/vhds/NewsFeed/logs/gunicorn_error.log"
loglevel  = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s %(D)sμs'

# Process
proc_name = "newsfeed"
preload_app = True
