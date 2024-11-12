let current_https_status = false;

const loader = document.querySelector('.loader');
loader.style.display = 'none';

const toggleDisableButtons = () => {
    const buttons = document.querySelectorAll('.button');
    for (btn of buttons) {
        btn.disabled = !btn.disabled;
    }
}

const toggleHttps = () => {
    current_https_status = !current_https_status;
    httpsButton.classList.remove('https-disabled');
    httpsButton.classList.remove('https-enabled');
    if (current_https_status) {
        httpsButton.classList.add('https-enabled');
    }
    else {
        httpsButton.classList.add('https-disabled');
    }
}

const sendRequest = async (path, requestData = null, method = 'GET') => {
    const controller = new AbortController();
    const signal = controller.signal;
    const timeoutId = setTimeout(() => controller.abort(), 5000);
    try {
        const params = {method: method, body: requestData};
        if (requestData)  {
            params.headers = {
                'Content-Type': 'text/plain'
            }
        }
        const response = await fetch(path, {...params, signal});
        clearTimeout(timeoutId);
        return response;
    } catch (e) {
        console.log(e);
        return null;
    }
}

const getRequest = async () => {
    toggleDisableButtons();
    loader.style.display = 'block';
    const request_id = Number(document.querySelector('.input').value);
    if (request_id === Number('a')) return;

    const requestData = await sendRequest('/request/' + request_id);
    const isHttpsResponse = await sendRequest('/request_json/' + request_id);
    if (isHttpsResponse.ok) {
        const res = await isHttpsResponse.json();
        if (res.proxied_over_https !== undefined && current_https_status !== res.proxied_over_https) {
            console.log(current_https_status);
            toggleHttps();
            current_https_status = res.proxied_over_https ?? false;
            console.log(current_https_status);
        }
    }
    const responseData = await sendRequest('/response/' + request_id);

    if (responseData.ok) {
        const res = await responseData.text();
        result = JSON.parse(res);
        const responseArea = document.querySelector('.response');
        if (!result.err) {
            responseArea.value = 'status: ' + result.code + '\n';
            for (header in result.headers) {
                responseArea.value += header + ': ' + result.headers[header] + '\n';
            }
            responseArea.value += result.body;
        } else {
            responseArea.value = '';
        }
    }

    if (requestData.ok) {
        const res = await requestData.text();
        const textArea = document.querySelector('.request');
        textArea.value = res;
    }
    toggleDisableButtons();
    loader.style.display = 'none';
}

const resendRequest = async () => {
    toggleDisableButtons();
    loader.style.display = 'block';
    requestData = document.querySelector('.request').value;
    if (current_https_status) {
        requestData += 'proxied_over_https'
    }
    const responseData = await sendRequest('/repeat_request', requestData, 'POST');
    if (responseData) {
        const res = await responseData.text();
        const responseArea = document.querySelector('.response');
        responseArea.value = res;
        if (res.length < 20) responseArea.value = '';
    }
    toggleDisableButtons();
    loader.style.display = 'none';
}

const doScan = async () => {
    toggleDisableButtons();
    loader.style.display = 'block';
    requestData = document.querySelector('.request').value;
    if (current_https_status) {
        requestData += 'proxied_over_https'
    }
    const responseData = await sendRequest('/xss_scan', requestData, 'POST');
    if (responseData) {
        const res = await responseData.json();
        const responseArea = document.querySelector('.response');
        responseArea.value = '';
        if (Object.keys(res).length === 0) {
            responseArea.value = 'No vulnerable params';
        }
        else {
            for (key in res) {
                responseArea.value += key + ': ' + res[key];
            }
        }
    }
    toggleDisableButtons();
    loader.style.display = 'none';
}

const getButton = document.querySelectorAll('.button')[0];
getButton.addEventListener('click', getRequest);

const sendButton = document.querySelectorAll('.button')[1];
sendButton.addEventListener('click', resendRequest);

const xssButton = document.querySelectorAll('.button')[2];
xssButton.addEventListener('click', doScan);

const httpsButton = document.querySelectorAll('.button')[3];
httpsButton.addEventListener('click', toggleHttps);