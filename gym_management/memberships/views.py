from django.shortcuts import render
from rest_framework import viewsets, generics, status
from rest_framework.permissions import IsAuthenticated
from .models import Membership
from .serializers import MembershipSerializer, MembershipCreateSerializer, MembershipUpdateSerializer

from users.permissions import AdminOnly,  StaffOrAdmin, IsSelfOrAdmin
from rest_framework.response import Response
from django.db import transaction


#CRUD operations for Memberships
class MembershipViewSet(viewsets.ModelViewSet):
    queryset = Membership.objects.all()

    #user different serializer for create
    def get_serializer_class(self):
        if self.action == 'create':
            return MembershipCreateSerializer
        return MembershipSerializer
    
    #permision based for an action
    def get_permissions(self):
        if self.action == 'destroy':
            permission_classes = [AdminOnly]
       
        elif self.action=='create':
            permission_classes = [IsAuthenticated, StaffOrAdmin]
        else:  
            permission_classes =[IsAuthenticated, StaffOrAdmin]
        return [perm() for perm in permission_classes]
    #custome create with explicit response
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        membership = serializer.save()
        

        read_serializer = MembershipSerializer(membership)
        return Response(read_serializer.data,
                        status=status.HTTP_201_CREATED)
    def destroy(self, request, *args, **kwargs):
        membership = self.get_object()
        
        membership.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    #members ristricted to see only their own memberships
    def get_queryset(self):
        user = self.request.user
        if user.role == 'member':
            return Membership.objects.filter(user=user)
        return Membership.objects.all()


#Handles safe updates to memberships
class MembershipUpdateView(generics.UpdateAPIView):
    queryset = Membership.objects.all()
    serializer_class = MembershipUpdateSerializer
    permission_classes = [StaffOrAdmin]
    
    def update(self, request, *args, **kwargs):
        membership = self.get_object()
        
        with transaction.atomic():
          
            locked_membership = Membership.objects.select_for_update().get(pk=membership.pk)
            serializer = self.get_serializer(locked_membership, data=request.data)
            serializer.is_valid(raise_exception=True)
           
            old_plan = locked_membership.plan_type
            old_expiry = locked_membership.expiration_date
            
       
            self.perform_update(serializer)
            updated_membership = serializer.instance
            

            print(f"\n=== MEMBERSHIP UPDATE ACTIVITY ===")
            print(f"Action: MEMBERSHIP_UPDATED")
            print(f"Performed by: {request.user} (ID: {request.user.id})")
            print(f"Target user: {updated_membership.user} (ID: {updated_membership.user.id})")
            print(f"Old plan: {old_plan}, New plan: {updated_membership.plan_type}")
            print(f"Old expiry: {old_expiry}, New expiry: {updated_membership.expiration_date}")
            print("==================================\n")
        
        return Response(serializer.data,
                        status=status.HTTP_200_OK)