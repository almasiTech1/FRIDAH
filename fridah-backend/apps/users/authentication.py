from rest_framework.exceptions import PermissionDenied
from rest_framework_simplejwt.authentication import JWTAuthentication

# While a temporary password is in force the account may do nothing except replace it.
ALLOWED_PATH_SUFFIXES = (
    '/auth/change-password/', '/auth/logout/', '/auth/refresh/', '/me/',
)


class PasswordChangeRequired(PermissionDenied):
    default_code = 'password_change_required'
    default_detail = 'You must change your temporary password before continuing.'


class FridahJWTAuthentication(JWTAuthentication):
    """
    JWT auth that refuses every request from an account still on an admin-issued temporary
    password, except changing it (and reading the profile / logging out). Enforced here, in the
    API, so it cannot be bypassed by skipping the front-end prompt.
    """
    def authenticate(self, request):
        result = super().authenticate(request)
        if result is None:
            return None
        user, token = result
        if getattr(user, 'must_change_password', False) and not request.path.endswith(ALLOWED_PATH_SUFFIXES):
            raise PasswordChangeRequired()
        return user, token
