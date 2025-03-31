FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies for SSL and certificates
RUN apt-get update && \
    apt-get install -y gcc libssl-dev curl ca-certificates && \
    update-ca-certificates

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Expose port (if needed)
EXPOSE 8000

# Run the bot
CMD ["python", "bot.py"]
