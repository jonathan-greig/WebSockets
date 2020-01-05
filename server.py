#!/usr/bin/env python3

import socket
import websocket
import sys

def serve():
    host = sys.argv[1]
    port = int(sys.argv[2])
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((host, port))
    sock.listen()
    conn, addr = sock.accept()

    handshake_request = conn.recv(2048)
    print('-'*20)
    print('Received handshake request:\n')
    print(handshake_request.decode())
    handshake_response = websocket.generate_server_handshake(handshake_request)
    conn.sendall(handshake_response)

    while(1):
        opcode, payload, fin = websocket.decode_frame_from_sock(conn)
        if (opcode == 1):
            payload = payload.decode('utf-8')
            response_frame = websocket.encode_frame(
                    websocket.OPCODES.index('text'), payload, False, False)
            conn.send(response_frame)
        else:
            break

if __name__ == '__main__':
    serve()
