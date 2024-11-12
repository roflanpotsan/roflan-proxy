import os
import subprocess
import time
from pathlib import Path
from uuid import uuid4


def generate_ca_certificate():
    Path('./cert').mkdir(parents=True, exist_ok=True)
    Path('./cert/ca').mkdir(parents=True, exist_ok=True)
    Path('./cert/www').mkdir(parents=True, exist_ok=True)
    if not os.path.exists('./cert/ca/ca.key') or not os.path.exists('./cert/ca/ca.crt'):
        subprocess.run(['./generate_ca.sh'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # time.sleep(1)
        print("Generated CA certificate and key.")
    # else:
    #     print("CA certificate and key already exist.")


def generate_server_certificate(domain):
    Path('./cert').mkdir(parents=True, exist_ok=True)
    Path('./cert/ca').mkdir(parents=True, exist_ok=True)
    Path('./cert/www').mkdir(parents=True, exist_ok=True)
    cert_path = os.path.join('./cert/www/', f'{domain}.crt')
    key_path = os.path.join('./cert/www/', f'{domain}.key')
    if not os.path.exists(cert_path) or not os.path.exists(key_path):
        subprocess.run(['./generate_server_cert.sh', './cert/ca/ca.key', './cert/ca/ca.crt', domain],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # time.sleep(1)
        print(f"Generated certificate for {domain}.")
    # else:
        # print(f"Certificate for {domain} already exists.")


# generate_ca_certificate()
# generate_server_certificate('mai1l.ru')
