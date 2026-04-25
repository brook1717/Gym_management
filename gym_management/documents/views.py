from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser

from .models import Document
from .serializers import DocumentSerializer
from users.permissions import StaffOrAdmin
from activity_logs.utils import log_activity


class DocumentViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentSerializer
    parser_classes = [MultiPartParser, FormParser]

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAuthenticated(), StaffOrAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'member':
            return Document.objects.filter(member=user)
        return Document.objects.all()

    def perform_create(self, serializer):
        document = serializer.save()
        log_activity(
            user=self.request.user,
            action='DOCUMENT_UPLOADED',
            target_type='document',
            target_id=document.id,
            metadata={'title': document.title, 'member_id': document.member.id},
            request=self.request
        )

    def perform_destroy(self, instance):
        metadata = {'document_id': instance.id, 'title': instance.title, 'member_id': instance.member.id}
        instance.file.delete(save=False)
        instance.delete()
        log_activity(
            user=self.request.user,
            action='DOCUMENT_DELETED',
            target_type='document',
            target_id=metadata['document_id'],
            metadata=metadata,
            request=self.request
        )
