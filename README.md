# Roflan-proxy

Простой прокси для HTTP запросов.

## Как запустить

В корне проекта запустить docker-контейнеры

`docker compose up --build`

По адресу `http://127.0.0.1:8889` - веб версия (web gui)

По адресу `http://127.0.0.1:8888` - прокси

## Функционал

### WEB GUI

<img width="1512" alt="Screenshot 2024-11-13 at 02 36 25" src="https://github.com/user-attachments/assets/4fd48651-f348-4a7b-ade2-7f3392253ae9">


### HTTP и HTTPS

Проксирует HTTP и HTTPS запросы. 

Для того, чтобы включить HTTPS нужно нажать на кнопку `HTTPS` (должа стать зеленой), чтобы выключить - аналогично (должна стать красной).

В **левом окне** запрос (который можно редактировать), в **правом** - ответ.

### Хранение запросов в БД

Запросы(с ответом) сохраняются в БД и их можно загрузить вместе с ответом нажав кнопку  `load request`, введя при этом номер запроса.

Для того, чтобы отправить запрос, нужно нажать `send_request`, при этом отправится тот запрос, который сейчас в **левом окне**.

### XSS Scan

Так же есть сканер XSS (правда только с одним пейлоадом, захардкоженом на беке, но свои пейлоады можно вставлять вручную, редактируя запрос).

Он проверяет все параметры и в качестве ответа в **правом окне** отображаются уязвимые параметры.

Для проверки можно запустить сканер на 

> `/vulnerable?param=...`

на хосте web gui (либо IP устройства, на котором запушщен контейнер в вашей сети, либо `host.docker.internal:8889`).