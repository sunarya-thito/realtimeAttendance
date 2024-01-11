import asyncio
import json
import websockets
import threading

websocket_server = None

connection_pool = set()

class Packet:
    def toMap(self):
        pass

class HadirPacket(Packet):
    def __init__(self, id):
        self.id = id

    def toMap(self):
        return {
            'packet_type': 'hadir',
            'id': self.id
        }
async def echo(websocket, path):
    connection_pool.add(websocket)
    try:
        async for message in websocket:
            print(message)
    finally:
        connection_pool.remove(websocket)

async def start_server():
    async with websockets.serve(echo, "localhost", 8777):
        print('websocket server started')
        await asyncio.Future()
        print('websocket server stopped')

def broadcast_packet(packet: Packet):
    websockets.broadcast(connection_pool, json.dumps(packet.toMap()))
