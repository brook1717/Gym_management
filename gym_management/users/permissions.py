from rest_framework.permissions import BasePermission

class AdminOnly(BasePermission):
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'admin'

class StaffOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['staff', 'admin']



class IsSelfOrAdmin(BasePermission):

    def has_object_permission(self, request, view, obj):
        return request.user.role == 'admin' or obj.id == request.user.id
