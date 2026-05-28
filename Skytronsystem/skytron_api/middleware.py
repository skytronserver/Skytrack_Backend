#middleware.py
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from django.utils.deprecation import MiddlewareMixin
from django.db import close_old_connections
from .models import RequestLog


# Best-effort async logging so slow DB writes don't block API responses.
_request_log_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix='request-log')


def _write_request_log(log_data):
    close_old_connections()
    try:
        RequestLog.objects.create(
            ip_address=log_data.get('ip_address'),
            system_info=log_data.get('system_info'),
            request_url=log_data.get('request_url'),
            request_type=log_data.get('request_type'),
            headers=json.dumps(log_data.get('headers')),
            incoming_data=json.dumps(log_data.get('incoming_data')),
            response_type=log_data.get('response_type'),
            response_time_ms=log_data.get('response_time_ms'),
            error_code=log_data.get('error_code')
        )
    except Exception:
        # Fallback: try without response_time_ms in case schema lags behind code.
        try:
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
        except Exception:
            pass
    finally:
        close_old_connections()


def _submit_request_log(log_data):
    try:
        _request_log_executor.submit(_write_request_log, dict(log_data))
    except Exception:
        pass

class RequestLoggerMiddleware(MiddlewareMixin):

    _SKIP_PATH_PREFIXES = (
        '/api/mqtt/validate-connection/',
        '/api/mqtt/validate-acl/',
    )

    @staticmethod
    def _get_client_ip(request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('HTTP_X_REAL_IP') or request.META.get('REMOTE_ADDR')

    def process_request(self, request):
        request._skip_request_log = any(
            request.path.startswith(prefix) for prefix in self._SKIP_PATH_PREFIXES
        )

        # Store request data in request object for later use
        request.start_time = datetime.now()
        request.log_data = {
            'ip_address': self._get_client_ip(request),
            'system_info': request.META.get('HTTP_USER_AGENT', 'unknown'),
            'request_url': request.build_absolute_uri(),
            'request_type': request.method,
            'headers': dict(request.headers),
            'incoming_data': str(request.body) if request.body else {}
        }

    def process_response(self, request, response):
        if getattr(request, '_skip_request_log', False):
            return response

        response_time_ms = None
        start_time = getattr(request, 'start_time', None)
        if start_time:
            response_time_ms = max(0, int((datetime.now() - start_time).total_seconds() * 1000))

        log_data = getattr(request, 'log_data', {})
        log_data.update({
            'response_type': response.get('Content-Type', 'unknown'),
            'response_time_ms': response_time_ms,
            'error_code': response.status_code if response.status_code >= 400 else None
        })
        _submit_request_log(log_data)
        return response

    def process_exception(self, request, exception):
        if getattr(request, '_skip_request_log', False):
            return

        response_time_ms = None
        start_time = getattr(request, 'start_time', None)
        if start_time:
            response_time_ms = max(0, int((datetime.now() - start_time).total_seconds() * 1000))

        log_data = getattr(request, 'log_data', {})
        log_data.update({
            'response_type': 'exception',
            'response_time_ms': response_time_ms,
            'error_code': 500,
            'response_data': str(exception)
        })
        _submit_request_log(log_data)