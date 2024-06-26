# asyncio_server
Клиент-серверное приложение на соккетах (asyncio), менеджер виртуальных машин.
Создана БД с двумя таблицами: virtual_machines и disks.
Для хранения используется PostgresSQL, все запросы написаны с использованием Asyncpg без каких-либо ОРМ.

## Инструкция:
Перед отправкой запросов необходимо установить зависимости и запустить сервер:
```
pip install -r requirements.txt
```
```
python server.py
```
После чего запросы отправляются по url:
```
http://localhost:8888/
```
С помощью POST-запросов можно авторизоваться, установить подключение, получить списки (авторизованные, подключенные, когда-либо подключаемые) виртуальных машин, а также дисков.

## Примеры запросов:
Добавление ВМ
```
{"action": "add_vm", "ram": 2048, "disks": [100, 200]}
```
Список всех ВМ
```
{"action": "list_all_vms"}
```
Список всех дисков
```
{"action": "list_all_disks"}
```
Добавление ВМ
```
{"action": "add_vm", "ram": 1028, "disks": [300]}
```
```
{"action": "add_vm", "ram": 4096, "disks": [500, 400]}
```
Авторизация ВМ
```
{"action": "authenticate", "vm_id": 1}
```
Подключение к ВМ
```
{"action": "connect", "vm_id": 2}
```
```
{"action": "connect", "vm_id": 3}
```
Список авторизованных ВМ
```
{"action": "list_authorized_vms"}
```
Список подключений
```
{"action": "list_connected_vms"}
```
Выход из ВМ
```
{"action": "logout_vm", "vm_id": 2}
```
Список подключенных ВМ
```
{"action": "list_connected_vms"}
```
Список когда-либо подключенных ВМ
```
{"action": "list_ever_connected"}
```
Частичное или полное обновление ВМ
```
{"action": "update_vm", "vm_id": 1, "ram": 1028}
```

### Краевые случаи:
Если не установлено подключение к ВМ, или не переданы данные
```
{"action": "update_vm", "vm_id": 1}

Ошибка: не установлено подключение к ВМ
{"error": "vm not authenticated"}

Ошибка: не переданы данные
{'error': 'required data: ram, disks'}
```
Подключение к несуществующей ВМ
```
{"action": "authenticate", "vm_id": 11231}

Ошибка: Не существует ВМ
{'error': 'VM ID does not exist'}
```
Добавление ВМ с некорректными данными
```
{"action": "add_vm", "ram": 2048}

Ошибка: не переданы данные
{'error': 'required data: ram, disks'}
```
