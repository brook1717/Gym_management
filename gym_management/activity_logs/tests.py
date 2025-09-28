# activity_logs/tests.py
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from .models import ActivityLog

User = get_user_model()

class ActivityLogTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(username='admin', email='a@example.com', password='pass', role='admin')
        self.staff = User.objects.create_user(username='staff', email='s@example.com', password='pass', role='staff')
        self.member = User.objects.create_user(username='member', email='m@example.com', password='pass', role='member')

    def test_admin_can_list_logs(self):
        # create a log
        ActivityLog.objects.create(action='TEST_ACTION', metadata={'x': 1}, user=self.admin)
        self.client.force_authenticate(self.admin)
        resp = self.client.get(reverse('activity-log-list'))
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(resp.data.get('count', 0), 1)

    def test_non_admin_cannot_list_logs(self):
        self.client.force_authenticate(self.member)
        resp = self.client.get(reverse('activity-log-list'))
        self.assertIn(resp.status_code, (403, 401))
