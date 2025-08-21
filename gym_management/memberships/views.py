from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Membership
from .serializers import MembershipSerializer

from users.permissions import AdminOnly,  StaffOrAdmin, IsSelfOrAdmin



class MembershipViewSet(viewsets.ModelViewSet):
    queryset = Membership.objects.all()
    serializer_class = MembershipSerializer

    def get_permissions(self):
       
        if self.action == 'destroy':
            permission_classes = [AdminOnly]
       
        else:
            permission_classes = [IsAuthenticated, StaffOrAdmin]
        return [perm() for perm in permission_classes]
