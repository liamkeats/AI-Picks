FROM python:3.12-slim

WORKDIR /app

# Add CA certs and build tools
RUN apt-get update && \
    apt-get install -y gcc libssl-dev curl ca-certificates && \
    update-ca-certificates

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "bot.py"]
