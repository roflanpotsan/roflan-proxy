import gzip
import re
import zlib
import brotli


def parse_request(req):
    """Parses an HTTP request directly as a byte string."""
    lines = re.split(b'\r\n|\n|\r', req)

    get_params = {}
    first_line = lines[0].split(b' ')
    method = first_line[0]
    path = b''
    version = b''

    if len(first_line) >= 3:
        first_line[1] = b' '.join(first_line[1:-1])
        first_line[2] = first_line[-1]
        while len(first_line) > 3:
            first_line.pop()

    if len(first_line) > 1:
        start_index = first_line[1].find(b'://')
        slash_index = first_line[1].find(b'/', start_index + 3 if start_index != -1 else 0)
        if slash_index == -1:
            slash_index = len(first_line[1])
        question_mark_index = first_line[1].find(b'?', start_index + 3 if start_index != -1 else 0)
        if question_mark_index == -1:
            question_mark_index = len(first_line[1])
        path = b'/' + first_line[1][slash_index + 1:question_mark_index]
        params = first_line[1][question_mark_index + 1:].split(b'&')
        if question_mark_index < len(first_line[1]):
            get_params = {param.split(b'=')[0]: b'='.join(param.split(b'=')[1:])for param in params if b'=' in param}

    if len(first_line) > 2:
        version = first_line[2]

    headers = {}
    cookies = {}
    post_params = {}
    body = b''
    body_parse = False

    for line in lines[1:]:
        if len(line) == 0:
            body_parse = True
            continue
        if not body_parse:
            split_line = line.split(b': ', 1)
            if len(split_line) == 2:
                header_name = split_line[0].decode('utf-8', errors='ignore')
                header_value = split_line[1].decode('utf-8', errors='ignore')
                if header_name == 'Cookie':
                    raw_cookies = header_value.split('; ')
                    cookies = {cookie.split('=')[0]: cookie.split('=')[1] for cookie in raw_cookies if '=' in cookie}
                elif header_name != 'Proxy-Connection':
                    headers[header_name] = header_value
        else:
            body += line + b'\n'

    body = body.rstrip(b'\n')

    if headers.get("Content-Type") == "application/x-www-form-urlencoded":
        post_params = {
            param.split(b'=')[0].decode('utf-8', errors='ignore').strip(): param.split(b'=')[1].decode('utf-8', errors='ignore').strip()
            for param in body.split(b'&') if b'=' in param
        }

    parsed_request = {
        "method": method.decode('utf-8', errors='ignore'),
        "path": path.decode('utf-8', errors='ignore'),
        "version": version.decode('utf-8', errors='ignore'),
        "headers": headers,
        "cookies": cookies,
        "get_params": {k.decode('utf-8', errors='ignore'): v.decode('utf-8', errors='ignore') for k, v in get_params.items()},
        "post_params": post_params,
        "body": body.decode('utf-8', errors='ignore')
    }

    return parsed_request


def reconstruct_request(parsed_request):
    path = parsed_request['path']
    if parsed_request['get_params']:
        path += '?' + '&'.join([f"{key}={value}" for key, value in parsed_request['get_params'].items()])
    first_line = f"{parsed_request['method']} {path} {parsed_request['version']}"

    headers = ""
    for key, value in parsed_request['headers'].items():
        headers += f"{key}: {value}\r\n"

    if parsed_request['cookies']:
        cookie_header = "Cookie: " + "; ".join([f"{key}={value}" for key, value in parsed_request['cookies'].items()])
        headers += f"{cookie_header}\r\n"

    body = parsed_request['body']
    if parsed_request['post_params']:
        body = '&'.join([f"{key}={value}" for key, value in parsed_request['post_params'].items()])

    reconstructed_request = f"{first_line}\r\n{headers}\r\n{body}"

    return reconstructed_request


def parse_response(response):
    """Parses an HTTP response directly as a byte string."""
    lines = response.split(b'\r\n')

    status_line = lines[0].split(b' ', 2)
    version = status_line[0]
    code = int(status_line[1])
    message = status_line[2] if len(status_line) > 2 else b''

    headers = {}
    body = b''
    body_parse = False

    for line in lines[1:]:
        if len(line) == 0:
            body_parse = True
            continue
        if not body_parse:
            split_line = line.split(b': ', 1)
            if len(split_line) == 2:
                headers[split_line[0].decode('utf-8', errors='ignore')] = split_line[1].decode('utf-8', errors='ignore')
        else:
            body += line + b'\n'

    body = body.rstrip(b'\n')

    if 'Content-Encoding' in headers:
        encoding = headers['Content-Encoding'].lower()
        try:
            if encoding == 'gzip':
                body = gzip.decompress(body)
            elif encoding == 'deflate':
                body = zlib.decompress(body)
            elif encoding == 'br':
                body = brotli.decompress(body)
        except (OSError, brotli.error) as e:
            print(f"Error decoding {encoding} content: {e}")

    try:
        body = body.decode('utf-8')
    except UnicodeDecodeError:
        body = body.decode('iso-8859-1')

    parsed_response = {
        "version": version.decode('utf-8', errors='ignore'),
        "code": code,
        "message": message.decode('utf-8', errors='ignore'),
        "headers": headers,
        "body": body
    }

    return parsed_response
