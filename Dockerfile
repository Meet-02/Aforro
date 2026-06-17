FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (layer caching — only rebuilds if requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the Django project into the container
COPY . .

EXPOSE 8000