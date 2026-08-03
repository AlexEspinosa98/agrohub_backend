class RequestLoggingMiddleware:
    """Prints method/path/body for every request — port of main.py's
    @app.middleware("http") log_requests in the old FastAPI backend."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        body = request.body.decode("utf-8", errors="ignore") if request.body else ""
        print(f" Request to {request.build_absolute_uri()} | Body: {body}")
        return self.get_response(request)
