from rest_framework.permissions import BasePermission


class AdminOnly(BasePermission):

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'admin'

    def has_object_permission(self, request, view, obj):
        return request.user.role == 'admin'


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

