from flask import Flask, jsonify, render_template, request
import subprocess
import shlex
import urllib.parse

import parser
from proxy import init_database
app = Flask(__name__)

client = init_database()
proxy = 'http://host.docker.internal:8888'


def get_item_by_id(database_client, shared_id, collection):
    db = database_client['proxy_db']
    collection = db[collection]
    request_ = collection.find_one({'shared_id': shared_id})
    return request_


@app.route('/', methods=['GET'])
def main():
    return render_template('main.html')


@app.route('/request/<int:request_id>', methods=['GET'])
def get_request(request_id):
    request_ = get_item_by_id(client, request_id, 'request')
    return parser.reconstruct_request(request_)


@app.route('/request_json/<int:request_id>', methods=['GET'])
def get_request_status(request_id):
    request_ = get_item_by_id(client, request_id, 'request')
    if request_:
        request_.pop('_id')
    else:
        return {"err": "nothing"}
    return request_


@app.route('/response/<int:response_id>', methods=['GET'])
def get_response(response_id):
    response = get_item_by_id(client, response_id, 'response')
    if response:
        response.pop('_id')
    else:
        return {"err": "nothing"}
    return response


@app.route('/repeat_request', methods=['POST'])
def resend_request():
    proxied_over_https = False
    data = request.data
    try:
        if data[-18:] == b'proxied_over_https':
            proxied_over_https = True
            data = data[:-18]
        request_data = parser.parse_request(data)

        method = request_data.get('method', 'GET')
        path = request_data.get('path', '/')
        headers = request_data.get('headers', {})
        cookies = request_data.get('cookies', {})
        get_params = request_data.get('get_params', {})
        body = request_data.get('body', '')

        protocol = 'https' if proxied_over_https else 'http'
        url = f"{protocol}://{headers['Host']}{path}"

        if get_params:
            query_string = '&'.join(f"{key}={urllib.parse.quote(value)}" for key, value in get_params.items())
            url = f"{url}?{query_string}"

        if cookies:
            cookie_string = '; '.join(f"{key}={value}" for key, value in cookies.items())
            headers['Cookie'] = cookie_string

        curl_command = f"curl -X {method} -x {proxy} -i {shlex.quote(url)}"

        for key, value in headers.items():
            curl_command += f" -H {shlex.quote(f'{key}: {value}')}"

        if method in ['POST', 'PUT'] and body:
            curl_command += f" --data {shlex.quote(body)}"
        print("final ", curl_command)
        try:
            result = subprocess.run(shlex.split(curl_command), capture_output=True, text=True)
            print("RESPONSE", result.stdout)
            response = result.stdout
            return '\n'.join(response.split('\n')[2:]), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    except Exception as e:
        return str(e)


@app.route('/xss_scan', methods=['POST'])
def scan():
    custom_string = """vulnerable'"><img src onerror=alert()>"""
    proxied_over_https = False
    data = request.data
    vulnerable_params = {}
    try:
        if data[-18:] == b'proxied_over_https':
            proxied_over_https = True
            data = data[:-18]
        request_data = parser.parse_request(data)

        method = request_data.get('method', 'GET')
        path = request_data.get('path', '/')
        headers = request_data.get('headers', {})
        cookies = request_data.get('cookies', {})
        get_params = request_data.get('get_params', {})
        post_params = request_data.get('post_params', {})
        body = request_data.get('body', '')

        protocol = 'https' if proxied_over_https else 'http'
        base_url = f"{protocol}://{headers['Host']}{path}"

        if cookies:
            cookie_string = '; '.join(f"{key}={value}" for key, value in cookies.items())
            headers['Cookie'] = cookie_string

        def send_request(modified_url, modified_body=None):
            curl_command = f"curl -X {method} -x {proxy} -i {shlex.quote(modified_url)}"

            for key, value in headers.items():
                curl_command += f" -H {shlex.quote(f'{key}: {value}')}"

            if method in ['POST', 'PUT'] and modified_body is not None:
                curl_command += f" --data {shlex.quote(modified_body)}"

            try:
                result = subprocess.run(shlex.split(curl_command), capture_output=True, text=True)
                response = result.stdout
                return response.find(custom_string)
            except Exception as e:
                print(f"Error sending request: {str(e)}")

        for key in get_params:
            modified_get_params = {**get_params, key: custom_string}
            query_string = '&'.join(f"{k}={urllib.parse.quote(v)}" for k, v in modified_get_params.items())
            modified_url = f"{base_url}?{query_string}"
            if send_request(modified_url) != -1:
                vulnerable_params[key] = 'get param vulnerable to XSS'

        if method in ['POST', 'PUT'] and post_params:
            for key in post_params:
                modified_post_params = {**post_params, key: custom_string}
                modified_body = '&'.join(f"{k}={urllib.parse.quote(v)}" for k, v in modified_post_params.items())
                if send_request(base_url, modified_body) != -1:
                    vulnerable_params[key] = 'post param vulnerable to XSS'

        return vulnerable_params, 200

    except Exception as e:
        return str(e), 500


@app.route('/vulnerable', methods=['GET'])
def vulnerable():
    param = request.args.get('param', 'nothing here')
    return render_template('vulnerable.html', extremely_vulnerable=param)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8889, debug=True)
