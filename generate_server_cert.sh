#!/bin/bash

# Variables
CA_KEY=$1
CA_CERT=$2
HOST=$3

# Generate server key
openssl genrsa -out "./cert/www/$HOST.key" 2048

openssl req -new -key "./cert/www/$HOST.key" -subj "/C=US/ST=State/L=Locality/O=roflan-proxy/CN=$HOST" -out "./cert/www/$HOST.csr"
openssl x509 -req -in "./cert/www/$HOST.csr" -CA "$CA_CERT" -CAkey "$CA_KEY" -CAcreateserial -out "./cert/www/$HOST.crt" -days 365 -sha256 -extfile <(echo "subjectAltName=DNS:$HOST")
rm "./cert/www/$HOST.csr"