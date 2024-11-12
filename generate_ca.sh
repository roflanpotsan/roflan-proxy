#!/bin/sh

openssl genrsa -out ./cert/ca/ca.key 2048

# Generate CA certificate (self-signed)
openssl req -new -x509 -days 3650 -key ca.key -subj "/C=US/ST=State/L=Locality/O=roflan-proxy CA/CN=roflan-proxy CA" -out ./cert/ca/ca.crt