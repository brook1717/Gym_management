from rest_framework.permissions import BasePermission, SAFE_METHODS


# ---------------------------------------------------------------------------
# Role-based permission classes
# ---------------------------------------------------------------------------

class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'admin'


class IsManager(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'manager'


class IsTrainer(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'trainer'


class IsReceptionist(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'receptionist'


# ---------------------------------------------------------------------------
# Composite role helpers (kept for backward compat & convenience)
# ---------------------------------------------------------------------------

# Legacy alias — same behaviour as IsAdmin
AdminOnly = IsAdmin


class ManagerOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['manager', 'admin']


class StaffLevel(BasePermission):
    """Allows Admin, Manager, Trainer, and Receptionist."""
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role in ['admin', 'manager', 'trainer', 'receptionist']
        )


class IsSelfOrAdmin(BasePermission):

    def has_permission(self, request, view):
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        return request.user.role == 'admin' or obj.id == request.user.id


# ---------------------------------------------------------------------------
# ABAC — Attribute-Based Access Control
# ---------------------------------------------------------------------------

class IsOwnerOrReadOnly(BasePermission):
    """
    Object-level permission: allows read access to any authenticated user,
    but write access only if ``request.user == obj.<owner_field>``.

    The owner field defaults to ``user`` but can be overridden per-view by
    setting ``owner_field`` on the view class, e.g.:

        class MyView(generics.UpdateAPIView):
            owner_field = "author"
    """

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        owner_field = getattr(view, 'owner_field', 'user')
        return request.user == getattr(obj, owner_field, None)

