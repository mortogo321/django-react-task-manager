from rest_framework import serializers

from .models import Notification, NotificationPreference


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id",
            "event",
            "title",
            "body",
            "payload",
            "read_at",
            "created_at",
        ]
        read_only_fields = fields


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = [
            "on_task_created",
            "on_task_status_changed",
            "on_task_completed",
            "on_task_overdue",
            "quiet_hours_start",
            "quiet_hours_end",
        ]
