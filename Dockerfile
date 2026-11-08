FROM python:3.11-slim

# Copy AWS Lambda Web Adapter extension
COPY --from=public.ecr.aws/awsguru/aws-lambda-adapter:0.8.4 /lambda-adapter /opt/extensions/lambda-adapter

# Configure AWS Lambda Web Adapter and runtime environment
ENV PORT=8000
ENV HOST=0.0.0.0
ENV FASTMCP_STATELESS_HTTP=true
ENV AWS_LWA_INVOKE_MODE=response_stream
ENV AWS_LWA_READINESS_CHECK_PATH=/health
ENV AWS_LWA_READ_TIMEOUT_MS=120000
ENV MPLCONFIGDIR=/tmp/matplotlib
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "mcp_server.py"]
