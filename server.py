import asyncio
import asyncpg
import json

DB_CONFIG = {
    'user': 'vms_user',
    'password': 'password',
    'database': 'vms_db',
    'host': '127.0.0.1',
    'port': 5432,
}


class VirtualMachineManager:
    def __init__(self):
        self.connected_vms = {}
        self.authorized_vms = {}
        self.ever_connected = []

    async def create_tables(self):
        conn = await asyncpg.connect(**DB_CONFIG)
        await conn.execute(
            '''
            CREATE SCHEMA IF NOT EXISTS vms_schema;
            CREATE TABLE IF NOT EXISTS vms_schema.virtual_machines (
                id SERIAL PRIMARY KEY,
                ram INTEGER NOT NULL,
                cpu INTEGER NOT NULL
            );
        '''
        )
        await conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS vms_schema.disks (
                id SERIAL PRIMARY KEY,
                vm_id INTEGER REFERENCES vms_schema.virtual_machines(id),
                size INTEGER NOT NULL
            );
        '''
        )
        await conn.close()
        print('Tables created or already exist.')

    async def add_vm(self, conn, ram, disks):
        cpu = len(disks)
        result = await conn.fetch(
            '''
            INSERT INTO vms_schema.virtual_machines(ram, cpu)
            VALUES($1, $2)
            RETURNING id
        ''',
            ram,
            cpu,
        )
        vm_id = result[0]['id']

        for size in disks:
            await conn.execute(
                '''
                INSERT INTO vms_schema.disks(vm_id, size)
                VALUES($1, $2)
            ''',
                vm_id,
                size,
            )
        await conn.close()
        print(f'VM ID {vm_id} added to db')

    async def connect_auth(self, request, conn, action, vm_id):
        result = await conn.fetchval(
            '''
            SELECT EXISTS(
                SELECT 1
                FROM vms_schema.virtual_machines
                WHERE id = $1
            )
            ''',
            vm_id,
        )
        await conn.close()
        if result:
            self.authorized_vms[vm_id] = request['vm_id']
            response = {'status': 'authenticated'}
            if action == 'connect':
                self.connected_vms[vm_id] = request['vm_id']
                self.authorized_vms[vm_id] = request['vm_id']
                self.ever_connected.append(vm_id)
                response = {'status': 'connected and authenticated'}
        else:
            response = {
                'error': 'VM ID does not exist',
            }
        return response

    async def list_ever_connected(self, conn):
        rows = await conn.fetch(
            '''
            SELECT
                vm.id, vm.ram, vm.cpu,
                COALESCE(json_agg(
                    json_build_object(
                        'id', d.id, 'size', d.size)) FILTER (
                            WHERE d.id IS NOT NULL), '[]') AS disks
            FROM vms_schema.virtual_machines vm
            LEFT JOIN vms_schema.disks d ON vm.id = d.vm_id
            WHERE vm.id = ANY($1)
            GROUP BY vm.id
            ''',
            self.ever_connected,
        )
        all_connected_vms = []
        for row in rows:
            vm = dict(row)
            vm['disks'] = json.loads(vm['disks'])
            all_connected_vms.append(vm)
        response = {'all_connected_vms': all_connected_vms}
        await conn.close()
        return response

    async def list_connected(self, conn):
        connected_vms = []
        for vm_id in self.connected_vms.keys():
            row = await conn.fetchrow(
                '''
                SELECT
                    vm.id, vm.ram, vm.cpu,
                    COALESCE(json_agg(
                        json_build_object(
                            'id', d.id, 'size', d.size)) FILTER (
                                WHERE d.id IS NOT NULL), '[]') AS disks
                FROM vms_schema.virtual_machines vm
                LEFT JOIN vms_schema.disks d ON vm.id = d.vm_id
                WHERE vm.id = $1
                GROUP BY vm.id
                ''',
                vm_id,
            )
            if row:
                vm = dict(row)
                vm['disks'] = json.loads(vm['disks'])
                connected_vms.append(vm)
        response = {'connected_vms': connected_vms}
        await conn.close()
        return response

    async def list_auth(self, conn):
        authorized_vms = []
        for vm_id in self.authorized_vms.keys():
            row = await conn.fetchrow(
                '''
                SELECT
                    vm.id, vm.ram, vm.cpu,
                    COALESCE(json_agg(
                        json_build_object(
                            'id', d.id, 'size', d.size)) FILTER (
                                WHERE d.id IS NOT NULL), '[]') AS disks
                FROM vms_schema.virtual_machines vm
                LEFT JOIN vms_schema.disks d ON vm.id = d.vm_id
                WHERE vm.id = $1
                GROUP BY vm.id
                ''',
                vm_id,
            )
            if row:
                vm = dict(row)
                vm['disks'] = json.loads(vm['disks'])
                authorized_vms.append(vm)
        response = {'authorized_vms': authorized_vms}
        await conn.close()
        return response

    async def list_all_vms(self, conn):
        rows = await conn.fetch(
            '''
            SELECT
                vm.id, vm.ram, vm.cpu,
                COALESCE(json_agg(
                    json_build_object(
                        'id', d.id, 'size', d.size)) FILTER (
                            WHERE d.id IS NOT NULL), '[]') AS disks
            FROM vms_schema.virtual_machines vm
            LEFT JOIN vms_schema.disks d ON vm.id = d.vm_id
            GROUP BY vm.id
            '''
        )
        all_vms = []
        for row in rows:
            vm = dict(row)
            vm['disks'] = json.loads(vm['disks'])
            all_vms.append(vm)
        response = {'all_vms': all_vms}
        await conn.close()
        return response

    async def logout(self, vm_id):
        if vm_id in self.authorized_vms:
            self.authorized_vms.pop(vm_id)
            self.connected_vms.pop(vm_id)
            response = {'status': 'logged_out'}
        else:
            response = {'error': 'vm not authenticated'}
        return response

    async def update_vm(self, conn, request, vm_id):
        if vm_id in self.authorized_vms:
            if 'ram' in request:
                ram = request['ram']
            else:
                ram = None
            if 'disks' in request:
                disks = request['disks']
                cpu = len(disks)
            else:
                disks = None
                cpu = None
            try:
                update_fields = []
                if ram is not None:
                    update_fields.append(f'ram = {ram}')
                if cpu is not None:
                    update_fields.append(f'cpu = {cpu}')
                if disks is not None:
                    for disk_id, size in disks.items():
                        update_fields.append(
                            f'size = {size} WHERE disk_id = {disk_id}'
                        )
                if update_fields:
                    update_query = (
                        'UPDATE vms_schema.virtual_machines SET '
                        + ', '.join(update_fields)
                        + f' WHERE id = {vm_id}'
                    )
                    await conn.execute(update_query)
                    if disks is not None:
                        for disk_id, size in disks.items():
                            await conn.execute(
                                '''
                                UPDATE vms_schema.disks
                                SET size = $1
                                WHERE disk_id = $2
                                AND id = $3
                                ''',
                                size,
                                disk_id,
                                vm_id,
                            )
                    response = {'status': 'vm updated'}
                else:
                    response = {'status': 'no updates'}
            finally:
                await conn.close()
        else:
            response = {'error': 'vm not authenticated'}
        return response

    async def list_all_disks(self, conn):
        rows = await conn.fetch('SELECT * FROM vms_schema.disks')
        response = {'all_disks': [dict(row) for row in rows]}
        await conn.close()
        return response

    async def get_request(self, reader, writer):
        conn = await asyncpg.connect(**DB_CONFIG)
        try:
            data = await reader.read(10000)
            message = data.decode('utf-8')
            json_start = message.find('\r\n\r\n') + 4
            json_data = message[json_start:]
            try:
                request = json.loads(json_data)
            except json.JSONDecodeError as e:
                print(f'Error decoding JSON: {e}')
                raise
            action = request.get('action')
            vm_id = request.get('vm_id')

            if action == 'authenticate' or action == 'connect':
                response = await self.connect_auth(
                    request, conn, action, vm_id
                )

            elif action == 'add_vm':
                try:
                    await self.add_vm(conn, request['ram'], request['disks'])
                    response = {'status': 'vm_added'}
                except Exception:
                    response = {'error': 'required data: ram, disks'}

            elif action == 'list_ever_connected':
                response = await self.list_ever_connected(conn)

            elif action == 'list_connected_vms':
                response = await self.list_connected(conn)

            elif action == 'list_authorized_vms':
                response = await self.list_auth(conn)

            elif action == 'list_all_vms':
                response = await self.list_all_vms(conn)

            elif action == 'logout_vm':
                response = await self.logout(vm_id)
            elif action == 'update_vm':
                response = await self.update_vm(conn, request, vm_id)
            elif action == 'list_all_disks':
                response = await self.list_all_disks(conn)
            else:
                response = {'error': 'invalid action'}

            writer.write('HTTP/1.1 200 OK\r\n'.encode())
            writer.write('Content-Type: application/json\r\n'.encode())
            writer.write('\r\n'.encode())
            writer.write(json.dumps(response).encode())
            await writer.drain()
        except Exception as e:
            print(f'Error: {e}')
            writer.write(json.dumps({'error': str(e)}).encode())
            await writer.drain()
        finally:
            writer.close()


async def main():
    vm_manager = VirtualMachineManager()
    await vm_manager.create_tables()
    server = await asyncio.start_server(
        vm_manager.get_request, '127.0.0.1', 8888
    )
    async with server:
        await server.serve_forever()


if __name__ == '__main__':
    asyncio.run(main())
