from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed
from rest_framework.authentication import CSRFCheck
from django.conf import settings


class CookieJWTAuthentication(JWTAuthentication):
    """
    Custom JWT authentication that reads the access token from an HttpOnly cookie
    instead of the Authorization header.

    Enforces CSRF validation on cookie-authenticated requests to prevent
    cross-site request forgery when using cookie-based token transport.
    """

    def authenticate(self, request):
        raw_token = request.COOKIES.get(settings.JWT_AUTH_COOKIE)
        if raw_token is None:
            return None

        try:
            validated_token = self.get_validated_token(raw_token)
        except InvalidToken:
            raise AuthenticationFailed("Invalid or expired access token.")

        # Enforce CSRF since authentication is cookie-based
        self._enforce_csrf(request)

        return self.get_user(validated_token), validated_token

    def _enforce_csrf(self, request):
        """
        Enforce CSRF validation for unsafe methods (POST, PUT, PATCH, DELETE).
        Safe methods (GET, HEAD, OPTIONS) are exempt.
        """
        if request.method in ("GET", "HEAD", "OPTIONS", "TRACE"):
            return

        check = CSRFCheck(self)
        # populates request.META["CSRF_COOKIE"] from the cookie
        check.process_request(request)
        reason = check.process_view(request, None, (), {})
        if reason:
            raise AuthenticationFailed(f"CSRF Failed: {reason}")
