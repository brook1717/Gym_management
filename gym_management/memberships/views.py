from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Membership
from .serializers import MembershipSerializer, MembershipCreateSerializer

from users.permissions import AdminOnly,  StaffOrAdmin, IsSelfOrAdmin
from rest_framework.response import Response



class MembershipViewSet(viewsets.ModelViewSet):
    queryset = Membership.objects.all()
    def get_serializer_class(self):
        if self.action == 'create':
            return MembershipCreateSerializer
        return MembershipSerializer

    def get_permissions(self):
       
        if self.action == 'destroy':
            permission_classes = [AdminOnly]
       
        elif self.action=='create':
            permission_classes = [IsAuthenticated, StaffOrAdmin]
        else:  
            permission_classes =[IsAuthenticated, StaffOrAdmin]
        return [perm() for perm in permission_classes]
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        membership = serializer.save()
        

        read_serializer = MembershipSerializer(membership)
        return Response(read_serializer.data)

    def get_queryset(self):
        user = self.request.user
        if user.role == 'member':
            return Membership.objects.filter(user=user)
        return Membership.objects.all()



