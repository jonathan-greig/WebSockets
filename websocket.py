#!/usr/bin/env python3

import socket
import ctypes
import struct
import hashlib
import base64

c_uint8 = ctypes.c_uint8
c_uint16 = ctypes.c_uint16

OPCODES = [
        'continuation',
        'text',
        'binary',
        'res1',
        'res2',
        'res3',
        'res4',
        'res5',
        'close',
        'ping',
        'pong',
        'res6',
        'res7',
        'res8',
        'res9',
        'resa'
        ]

class FrameHeaderBitField(ctypes.BigEndianStructure):
    _fields_ = [
            ("mask", c_uint8, 1),
            ("len_16", c_uint8, 7),
            ("fin", c_uint8, 1),
            ("rsv1", c_uint8, 1),
            ("rsv2", c_uint8, 1),
            ("rsv3", c_uint8, 1),
            ("opcode", c_uint8, 4)
            ]

class FrameHeader(ctypes.Union):
    _fields_ = [
            ("bitfield", FrameHeaderBitField),
            ("short", c_uint16)
            ]

    def __init__(self, frame_header_bytes=0):
        self.short = frame_header_bytes

def mask_payload(payload, mask_key=b'\xaa\xbb\xcc\xdd'):
    processed = bytearray(payload)
    for i, byte in enumerate(processed):
        processed[i] = byte ^ mask_key[i % 4]
    return (bytes(processed), mask_key)

def decode_complete_frame(frame):
    frame_header_bytes = struct.unpack('!H', frame[0:2])[0]
    frame_header = FrameHeader(frame_header_bytes)
    payload = b''
    
    print('-'*20)
    print(f'fin:  {frame_header.bitfield.fin}')
    print(f'opcode:  {frame_header.bitfield.opcode} '\
            f'({OPCODES[frame_header.bitfield.opcode]})')
    print(f'mask:  {frame_header.bitfield.mask}')
    print(f'len_16:  {frame_header.bitfield.len_16}')

    if frame_header.bitfield.len_16:
        if frame_header.bitfield.len_16 < 126:
            data_offset = 2
            payload_len = frame_header.bitfield.len_16

        elif frame_header.bitfield.len_16 == 126:
            data_offset = 4
            payload_len = struct.unpack('!H', frame[2:4])[0]

        elif frame_header.bitfield.len_16 == 127:
            data_offset = 10
            payload_len = struct.unpack('!Q', frame[2:10])[0]

        if frame_header.bitfield.mask:
            masking_key = frame[data_offset: data_offset + 4]
            print(f'masking_key:\t{masking_key}')
            payload = frame[data_offset + 4: data_offset + 4 + payload_len]
            payload = mask_payload(payload)[0]
        else:
            payload = frame[data_offset: data_offset + payload_len]

        close_reason = ''
        if payload and frame_header.bitfield.opcode == OPCODES.index('close'):
            close_reason = struct.unpack('!H', payload[0:2])[0]
            payload = payload[2:]

        print(f'payload_len:  {payload_len}')
        if close_reason:
            print(f'close_reason:  {close_reason}')
        print(f'payload:  {payload if len(payload) <= 100 else payload[:101]}')
    print('-'*20)

    return (frame_header.bitfield.opcode, payload.decode(),
            frame_header.bitfield.fin) 

def decode_frame_from_sock(sock):
    frame_header_bytes = b''
    while not frame_header_bytes:
        frame_header_bytes = sock.recv(2)
    frame_header_bytes = struct.unpack('!H', frame_header_bytes[0:2])[0]
    frame_header = FrameHeader(frame_header_bytes)
    payload = b''
    
    print('-'*20)
    print('Received frame:\n')
    print(f'fin:  {frame_header.bitfield.fin}')
    print(f'opcode:  {frame_header.bitfield.opcode} '\
            f'({OPCODES[frame_header.bitfield.opcode]})')
    print(f'mask:  {frame_header.bitfield.mask}')
    print(f'len_16:  {frame_header.bitfield.len_16}')

    if frame_header.bitfield.len_16:
        if frame_header.bitfield.len_16 < 126:
            data_offset = 2
            payload_len = frame_header.bitfield.len_16

        elif frame_header.bitfield.len_16 == 126:
            data_offset = 4
            payload_len = struct.unpack('!H', sock.recv(2))[0]

        elif frame_header.bitfield.len_16 == 127:
            data_offset = 10
            payload_len = struct.unpack('!Q', sock.recv(8))[0]

        if frame_header.bitfield.mask:
            masking_key = sock.recv(4)
            print(f'masking_key:\t{masking_key}')
            payload = sock.recv(payload_len) 
            payload = mask_payload(payload, masking_key)[0]
        else:
            payload = sock.recv(payload_len)

        close_reason = ''
        if payload and frame_header.bitfield.opcode == OPCODES.index('close'):
            close_reason = struct.unpack('!H', payload[0:2])[0]
            payload = payload[2:]

        print(f'payload_len:  {payload_len}')
        if close_reason:
            print(f'close_reason:  {close_reason}')
        print(f'payload:  {payload if len(payload) <= 100 else payload[:101]}')
    print('-'*20)

    return (frame_header.bitfield.opcode, payload,
            frame_header.bitfield.fin) 

def encode_frame(opcode=OPCODES.index('text'), payload=None, fragment=False,
        mask=True):
    frame = b''
    frame_header = FrameHeader()

    if fragment:
        frame_header.bitfield.fin = 0
    else:
        frame_header.bitfield.fin = 1

    frame_header.bitfield.opcode = opcode
   
    if payload:
        payload_len = len(payload)
        payload = payload.encode()
        if mask:
            frame_header.bitfield.mask = 1
            
        if payload_len < 126:
            frame_header.bitfield.len_16 = payload_len
            frame += struct.pack('!H', frame_header.short)
        elif payload_len > 125 and payload_len < 2 ** 16:
            frame_header.bitfield.len_16 = 126
            frame += struct.pack('!H', frame_header.short)
            frame += struct.pack('!H', payload_len)
        elif payload_len < 2 ** 64:
            frame_header.bitfield.len_16 = 127
            frame += struct.pack('!H', frame_header.short)
            frame += struct.pack('!Q', payload_len)

        if mask:
            payload, mask_key = mask_payload(payload)
            frame += mask_key

        frame += payload

    else:
        frame += struct.pack('!H', frame_header.short)

    return frame

def client_handshake(sock, host):
    client_handshake = \
            'GET / HTTP/1.1\r\n'\
            f'Host: {host}\r\n'\
            'Sec-WebSocket-Version: 13\r\n'\
            'Sec-WebSocket-Key: 3F9yYO/NTk78G+4MKUm5rA==\r\n'\
            'Connection: Upgrade\r\n'\
            'Upgrade: websocket\r\n\r\n'

    sock.sendall(client_handshake.encode())    
    handshake_response = sock.recv(2048)
    return handshake_response

def generate_server_handshake(client_handshake):
    request_line, headers = parse_client_handshake(client_handshake)
    handshake_response = 'HTTP/1.1 101 Switching Protocols\r\nUpgrade: '\
           'WebSocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: '\
           '{}\r\n\r\n'
    sec_websocket_key = headers[b'Sec-WebSocket-Key']
    sec_websocket_accept = generate_sec_websocket_accept(sec_websocket_key)
    handshake_response = handshake_response.format(sec_websocket_accept.decode())
    return handshake_response.encode()

def generate_sec_websocket_accept(sec_websocket_key):
    guid = b'258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
    sec_websocket_accept = sec_websocket_key + guid
    sha1 = hashlib.sha1()
    sha1.update(sec_websocket_accept)
    sec_websocket_accept = base64.b64encode(sha1.digest())
    return sec_websocket_accept

def parse_client_handshake(client_handshake):
    client_handshake = client_handshake.replace(b'\r',b'').split(b'\n')
    request_line = client_handshake[0].split(b' ')
    headers = {}
    for header in client_handshake[1:]:
        if header:
            header = header.split(b': ')
            headers[header[0]] = header[1]
    return request_line, headers 