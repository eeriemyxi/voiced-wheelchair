# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "pyserial",
#     "python-dotenv",
# ]
# ///
import serial
import socket
import os
import time
from dotenv import load_dotenv

load_dotenv()

COM_PORT = 'COM3'
BAUD_RATE = 9600
NETWORK_PORT = int(os.environ["BRIDGE_PORT"])

def start_bridge():
    ser = serial.Serial(COM_PORT, BAUD_RATE, timeout=0.1)
    
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('0.0.0.0', NETWORK_PORT))
    server.listen(5)
    server.settimeout(1.0)
    
    print(f"Bridge active. Listening on port {NETWORK_PORT} for Docker...")

    try:
        while True:
            try:
                conn, addr = server.accept()
                
                with conn:
                    data = conn.recv(1024)
                    if data:
                        ser.write(data)
                        
                        if ser.in_waiting > 0:
                            response = ser.read(ser.in_waiting)
                            conn.sendall(response)
                            
            except socket.timeout:
                continue 
            except Exception as e:
                print(f"Connection error: {e}")
                
    except KeyboardInterrupt:
        print("\nShutting down bridge cleanly...")
    finally:
        server.close()
        ser.close()

if __name__ == "__main__":
    start_bridge()