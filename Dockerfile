FROM python:3.12-slim

WORKDIR /app

COPY . .

RUN apt-get update && apt-get install -y curl && apt-get clean

RUN pip install --no-cache-dir -r requirements.txt

COPY cert/ca/ca.crt /usr/local/share/ca-certificates/

RUN chmod 644 /usr/local/share/ca-certificates/ca.crt && update-ca-certificates


CMD ["python", "api.py"]
