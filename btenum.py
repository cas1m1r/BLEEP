from bleak import BleakClient,BleakScanner
import asyncio
import random
import bleak
import json
import time


async def read_gatt_char(client, address, char_uuid):
    # Read the characteristic
    value = ''
    try:
        value = await client.read_gatt_char(char_uuid)
        print(f"Read value: {value.decode('utf-8')}")
    except:
        pass
    return value

async def run():
    devices = await BleakScanner.discover()
    enumeration = {}
    random.shuffle(devices)
    for d in devices:
        device_data = await enumerate_device(d.address)

        enumeration[d.address] = {'name': str(d.name),
                                  'details': device_data,
                                  'rssi': d.rssi}
    return enumeration


async def enumerate_device(address):
    device_data = {}
    try:
        async with BleakClient(address) as client:
            print('='*80)
            connected = client.is_connected
            print(f'Connecting to {address}')

            print(f"Connected: {connected}")
            device_data['connected'] = str(connected)
            services = await client.get_services()
            device_data['services'] = []
            for service in services:
                print(f"Service: {service.uuid}")
                service_data = {'uuid': str(service.uuid), 'characteristics': []}
                for characteristic in service.characteristics:
                    print(f"  Characteristic: {characteristic.uuid}")
                    attribute = await read_gatt_char(client, address,characteristic.uuid)
                    if type(attribute) == bytearray:
                        try:
                            data = attribute.decode('utf-8')
                        except:
                            data = attribute
                            pass
                    elif type(attribute) == str:
                        data = attribute
                    if len(data) >0:
                        service_data['characteristics'].append(data)
                device_data['services'].append(service_data)
        print(f'Disconnecting from {address}')

        try:
            await client.disconnect()
        except:
            pass
    except asyncio.exceptions.TimeoutError:
        pass
    except bleak.exc.BleakDeviceNotFoundError:
        print(f'Failed to connect to {address}')
        pass
    except bleak.exc.BleakError:
        print(f'Failed to connect to {address}')
        pass
    return device_data

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    enum_data = loop.run_until_complete(run())
    result = json.dumps(enum_data, indent=2)
    open(f'bluetooth_enumeration_{round(time.time())}.json','w').write(result)
