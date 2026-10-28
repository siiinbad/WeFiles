class PrivacyHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.headers.get("HX-Request") and response.status_code == 302:
            response["HX-Redirect"] = response["Location"]
            del response["Location"]
            response.status_code = 200
            response.content = b""
        response["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data:; font-src 'self'; connect-src 'self'; "
            "object-src 'none'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        )
        response["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response["X-Robots-Tag"] = "noindex, nofollow"
        if request.user.is_authenticated or request.path.startswith(("/accounts/", "/admin/")):
            response["Cache-Control"] = "private, no-store"
        return response
