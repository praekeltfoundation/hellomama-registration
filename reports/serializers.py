from django.conf import settings
from django.utils import timezone
from rest_framework import serializers
from reports.utils import midnight, midnight_validator, one_month_after
from .models import ReportTaskStatus


class ReportGenerationSerializer(serializers.Serializer):
    start_date = serializers.CharField(required=False)
    end_date = serializers.CharField(required=False)
    email_to = serializers.ListField(child=serializers.EmailField(),
                                     default=[])
    email_from = serializers.EmailField(default=settings.DEFAULT_FROM_EMAIL)
    email_subject = serializers.CharField(default='HelloMama Generated Report')

    def validate(self, data):
        if 'start_date' not in data:
            data['start_date'] = midnight(timezone.now())

        if 'end_date' not in data:
            data['end_date'] = one_month_after(data['start_date'])
        return data

    def validate_date(self, value):
        try:
            date = midnight_validator(value)
        except ValueError as e:
            raise serializers.ValidationError(str(e))
        return date

    def validate_start_date(self, value):
        return self.validate_date(value)

    def validate_end_date(self, value):
        return self.validate_date(value)


class ReportTaskStatusSerializer(serializers.ModelSerializer):

    class Meta:
        model = ReportTaskStatus
        read_only_fields = ('start_date', 'end_date', 'email_subject',
                            'file_size', 'status', 'error', 'created_at',
                            'updated_at')
        fields = ('start_date', 'end_date', 'email_subject', 'file_size',
                  'status', 'error', 'created_at', 'updated_at')
