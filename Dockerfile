FROM python:3.12-slim

# Make sure certs & curl are available for SSL to work
RUN apt-get update && apt-get install -y \
    gcc \
    libssl-dev \
    ca-certificates \
    curl \
 && update-ca-certificates

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "bot.py"]
