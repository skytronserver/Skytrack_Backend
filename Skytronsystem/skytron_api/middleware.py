#middleware.py
import json
from datetime import datetime

from django.utils.deprecation import MiddlewareMixin
from .models import RequestLog

class RequestLoggerMiddleware(MiddlewareMixin):

    def process_request(self, request):
        # Store request data in request object for later use
        request.start_time = datetime.now()
        request.log_data = {
            'ip_address': request.META.get('REMOTE_ADDR'),
            'system_info': request.META.get('HTTP_USER_AGENT', 'unknown'),
            'request_url': request.build_absolute_uri(),
            'request_type': request.method,
            'headers': dict(request.headers),
            'incoming_data': str(request.body) if request.body else {}
        }

    def process_response(self, request, response):
        log_data = getattr(request, 'log_data', {})
        log_data.update({
            'response_type': response.get('Content-Type', 'unknown'),
            'error_code': response.status_code if response.status_code >= 400 else None
        })
        RequestLog.objects.create(
            ip_address=log_data.get('ip_address'),
            system_info=log_data.get('system_info'),
            request_url=log_data.get('request_url'),
            request_type=log_data.get('request_type'),
            headers=json.dumps(log_data.get('headers')),
            incoming_data=json.dumps(log_data.get('incoming_data')),
            response_type=log_data.get('response_type'),
            error_code=log_data.get('error_code')
        )
        return response

    def process_exception(self, request, exception):
        log_data = getattr(request, 'log_data', {})
        log_data.update({
            'response_type': 'exception',
            'error_code': 500,
            'response_data': str(exception)
        })
        RequestLog.objects.create(
            ip_address=log_data.get('ip_address'),
            system_info=log_data.get('system_info'),
            request_url=log_data.get('request_url'),
            request_type=log_data.get('request_type'),
            headers=json.dumps(log_data.get('headers')),
            incoming_data=json.dumps(log_data.get('incoming_data')),
            response_type=log_data.get('response_type'),
            error_code=log_data.get('error_code')
        )