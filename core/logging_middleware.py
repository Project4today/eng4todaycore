import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import Message

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Store the request body to be used after the request is processed
        request_body = await self.get_request_body(request)

        start_time = time.time()
        
        # Process the request and get the response
        response = await call_next(request)
        
        process_time = time.time() - start_time
        
        # Log details after the response has been generated
        self.log_details(request, response, request_body, process_time)
        
        return response

    async def get_request_body(self, request: Request) -> bytes:
        """
        Reads the request body and leaves it available for subsequent reads.
        """
        body = await request.body()
        # To make the body readable again for the actual endpoint, we need to
        # create a new "receive" function.
        async def receive() -> Message:
            return {"type": "http.request", "body": body}
        request._receive = receive
        return body

    def log_details(self, request: Request, response: Response, body: bytes, process_time: float):
        """
        Formats and prints the log message.
        """
        log_message = (
            f"\n----- API Request Log -----\n"
            f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Method: {request.method}\n"
            f"URL: {request.url}\n"
            f"Client IP: {request.client.host}\n"
            f"Headers: {dict(request.headers)}\n"
        )

        if body:
            try:
                log_message += f"Request Body: {body.decode('utf-8')}\n"
            except UnicodeDecodeError:
                log_message += f"Request Body: [Non-UTF-8 data, size: {len(body)} bytes]\n"
        else:
            log_message += "Request Body: [Empty]\n"

        # Check for our custom bot version header in the response
        bot_version = response.headers.get("x-bot-version")
        if bot_version:
            log_message += f"Bot Version Used: {bot_version}\n"

        log_message += (
            f"---------------------------\n"
            f"Response Status: {response.status_code}\n"
            f"Process Time: {process_time:.4f}s\n"
            f"----- End Log -----\n"
        )
        
        print(log_message)
