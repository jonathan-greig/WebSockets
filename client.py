#!/usr/bin/env python3

import socket
import websocket
import sys

def main():
    if len(sys.argv) < 3:
        print('Usage: ./client.py host port\n'\
                'Example: ./client.py echo.websocket.org 80\n\n'\
                'Note: does not support TLS')
        quit()
    host = sys.argv[1]
    port = int(sys.argv[2])
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock = socket.create_connection((host, port))

    handshake_response = websocket.client_handshake(sock, host)
    print('-'*20)
    print('Received handshake response:\n')
    print(handshake_response.decode())
    print('type\'exit\' to close connection')

    while(1):
        payload = input('>> ')
        if payload == "exit":
            break
        frame = websocket.encode_frame(websocket.OPCODES.index('text'), 
                payload, False, True) 
        sock.sendall(frame)
        frame = websocket.decode_frame_from_sock(sock)

    frame = websocket.encode_frame(websocket.OPCODES.index('close'))
    sock.sendall(frame)
    frame = sock.recv(2048)

if __name__ == '__main__':
    main()
