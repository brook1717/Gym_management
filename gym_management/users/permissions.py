from rest_framework.permissions import BasePermission, SAFE_METHODS

class AdminOnly(BasePermission):
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'admin'
    def has_object_permission(self, request, view, obj):
        return request.user.role == 'admin' or obj.id == request.user.id

class StaffOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['staff', 'admin']

class IsSelfOrAdmin(BasePermission):

    def has_object_permission(self, request, view, obj):
        return request.user.role == 'admin' or obj.id == request.user.id

