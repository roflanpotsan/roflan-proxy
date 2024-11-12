import socket
import ssl
import threading

from parser import *
from cert_generator import *

from pymongo import MongoClient

HOST = '0.0.0.0'
PORT = 8888
MAX_RECEIVED_SIZE = 65536


def init_database():
    mongo_uri = os.getenv('MONGO_URI', 'mongodb://127.0.0.1:27017/')
    client = MongoClient(mongo_uri)
    return client


def get_next_shared_id(db):
    sequence_collection = db['counters']
    sequence = sequence_collection.find_one_and_update(
        {'_id': 'shared_id'},
        {'$inc': {'sequence_value': 1}},
        upsert=True,
        return_document=True
    )
    return sequence['sequence_value']


def handle_http_connection(client_socket, parsed_request, host, port, database_client):
    """Handles an HTTP connection by forwarding the request and relaying the response."""
    # Create a socket to connect to the destination server
    db = database_client['proxy_db']
    collection = db['request']
    try:
        parsed_request['shared_id'] = get_next_shared_id(db)
        if parsed_request.get('_id') is not None:
            del parsed_request['_id']
        collection.insert_one(parsed_request)
    except Exception:
        print('could not save req')
    data_accumulator = b''
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.connect((host, port))
        server_socket.settimeout(1)
        try:
            server_socket.send(reconstruct_request(parsed_request).encode('utf-8'))
            while True:
                response = server_socket.recv(MAX_RECEIVED_SIZE)
                if not response:
                    break
                data_accumulator += response
                client_socket.send(response)
        except Exception:
            client_socket.close()
    try:
        collection = db['response']
        latest_request = db['request'].find_one(sort=[('shared_id', -1)])
        parsed_response = parse_response(data_accumulator)
        parsed_response['shared_id'] = latest_request['shared_id']
        collection.insert_one(parsed_response)
    except Exception:
        print('could not save resp')
    client_socket.close()


# Cache for SSL contexts
ssl_context_cache = {}


def get_ssl_context(host):
    """Returns an SSL context for the given host, creating and caching it if necessary."""
    if host not in ssl_context_cache:
        generate_server_certificate(host)
        cert_file = f"./cert/www/{host}.crt"
        key_file = f"./cert/www/{host}.key"

        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        try:
            context.load_cert_chain(certfile=cert_file, keyfile=key_file)
            context.options |= ssl.OP_NO_SSLv2
            context.options |= ssl.OP_NO_SSLv3
            context.options |= ssl.OP_NO_TLSv1
            context.options |= ssl.OP_NO_TLSv1_1
        except Exception:
            return

        # Store the context in the cache
        ssl_context_cache[host] = context

    return ssl_context_cache[host]


def handle_https_connection(client_socket, parsed_request, host, port, database_client):
    """Handles an HTTPS connection by establishing an SSL tunnel and reusing SSL contexts."""
    context = get_ssl_context(host)
    if not context:
        return

    try:
        # Wrap the client socket to handle SSL traffic
        with context.wrap_socket(client_socket, server_side=True) as ssl_client_socket:
            # Establish a connection to the destination server
            with socket.create_connection((host, port)) as server_socket:
                with ssl.create_default_context().wrap_socket(server_socket,
                                                              server_hostname=host) as ssl_server_socket:
                    # Relay data between the client and the server
                    client_thread = threading.Thread(target=relay_data,
                                                     args=(ssl_client_socket, ssl_server_socket, database_client, True))
                    server_thread = threading.Thread(target=relay_data,
                                                     args=(ssl_server_socket, ssl_client_socket, database_client, False))

                    client_thread.start()
                    server_thread.start()

                    client_thread.join()
                    server_thread.join()
    except Exception as e:
        print(e)
        client_socket.close()
    finally:
        client_socket.close()


def relay_data(source_socket, destination_socket, database_client, is_request=True):
    """Relays data between two sockets, handling errors gracefully."""
    db = database_client['proxy_db']
    collection = db['request'] if is_request else db['response']
    data_accumulator = b''
    try:
        while True:
            data = source_socket.recv(MAX_RECEIVED_SIZE)
            if not data:
                break
            data_accumulator += data
            destination_socket.sendall(data)
    except (OSError, ssl.SSLError) as e:
        print(f"Relay error: {e}")
    except Exception as e:
        print(f"General relay error: {e}")
    finally:
        if is_request:
            try:
                parsed_request = parse_request(data_accumulator)
                parsed_request['shared_id'] = get_next_shared_id(db)
                parsed_request['proxied_over_https'] = True
                if parsed_request.get('_id') is not None:
                    del parsed_request['_id']
                collection.insert_one(parsed_request)
            except Exception:
                print('could not save req')
        else:
            try:
                latest_request = db['request'].find_one(sort=[('shared_id', -1)])
                parsed_response = parse_response(data_accumulator)
                parsed_response['shared_id'] = latest_request['shared_id']
                collection.insert_one(parsed_response)
            except Exception:
                print('could not save resp')
        close_socket_safe(source_socket)
        close_socket_safe(destination_socket)


def close_socket_safe(sock):
    """Closes the socket safely if it's not already closed."""
    try:
        if sock.fileno() != -1:  # Checks if the file descriptor is valid
            sock.close()
    except Exception as e:
        print(f"Error closing socket: {e}")


def handle_client(client_socket, database_client):
    """Parses the client request and dispatches HTTP or HTTPS handlers."""
    request = client_socket.recv(MAX_RECEIVED_SIZE)
    parsed_request = parse_request(request)
    try:
        host_info = parsed_request['headers']['Host'].split(':')
    except Exception:
        client_socket.close()
        return
    host = host_info[0]
    if parsed_request['method'] == 'CONNECT':
        # Handle HTTPS connection
        port = int(host_info[1]) if len(host_info) > 1 else 443
        client_socket.send(b"HTTP/1.1 200 Connection Established\r\n\r\n")
        handle_https_connection(client_socket, parsed_request, host, port, database_client)
    else:
        # Handle HTTP connection
        port = int(host_info[1]) if len(host_info) > 1 else 80
        handle_http_connection(client_socket, parsed_request, host, port, database_client)


def start_proxy_server(host, port):
    """Starts the proxy server to handle client connections."""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(100)
    print(f"Proxy server running on {host}:{port}")

    database_client = init_database()
    while True:
        client_socket, addr = server_socket.accept()
        print(f"Received connection from {addr}")
        client_handler = threading.Thread(target=handle_client, args=(client_socket, database_client))
        client_handler.start()


if __name__ == "__main__":
    start_proxy_server(HOST, PORT)
