import logging
logger = logging.getLogger(__name__)

class RequestLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Log request details
        logger.info(f'{request.method} {request.get_full_path()}')
        
        # Optionally log response details
        if response.status_code >= 400:  # only log errors
            logger.error(f'Response: {response.status_code} {response.reason_phrase}')

        return response