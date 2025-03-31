# Use a lightweight Python image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install system dependencies including SSL certs
RUN apt-get update && apt-get install -y gcc libssl-dev curl ca-certificates && \
    update-ca-certificates

# Copy requirements and install them
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project
COPY . .

# Command to run your bot
CMD ["python", "DiscordBot/bot.py"]
