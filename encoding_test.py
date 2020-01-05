#!/usr/bin/env python3

import websocket

def main():
    websocket.decode_complete_frame(websocket.encode_frame(1, 'a'*6))
    websocket.decode_complete_frame(websocket.encode_frame(1, 'a'*125))
    websocket.decode_complete_frame(websocket.encode_frame(1, 'a'*126))
    websocket.decode_complete_frame(websocket.encode_frame(1, 'a'*(2**16)))

if __name__ == '__main__':
    main()