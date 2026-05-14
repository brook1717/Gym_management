from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed
from django.conf import settings


class CookieJWTAuthentication(JWTAuthentication):
    """
    Custom JWT authentication that reads the access token from an HttpOnly cookie
    instead of the Authorization header.
    """

    def authenticate(self, request):
        raw_token = request.COOKIES.get(settings.JWT_AUTH_COOKIE)
        if raw_token is None:
            return None

        try:
            validated_token = self.get_validated_token(raw_token)
        except InvalidToken:
            raise AuthenticationFailed("Invalid or expired access token.")

        return self.get_user(validated_token), validated_token
