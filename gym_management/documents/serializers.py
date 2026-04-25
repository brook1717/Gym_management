from rest_framework import serializers
from .models import Document


class DocumentSerializer(serializers.ModelSerializer):
    member_name = serializers.CharField(source='member.full_name', read_only=True)

    class Meta:
        model = Document
        fields = ['id', 'member', 'member_name', 'title', 'file', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']
