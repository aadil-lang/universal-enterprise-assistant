FROM python:3.12-slim

WORKDIR /app

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create unprivileged runtime user
RUN groupadd -g 1001 mcpuser && \
    useradd -u 1001 -g mcpuser -s /bin/bash -m mcpuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
RUN chown -R mcpuser:mcpuser /app

# Switch to unprivileged runtime user
USER mcpuser

EXPOSE 8001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
