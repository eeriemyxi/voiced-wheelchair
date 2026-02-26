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
import threading
import time
from dotenv import load_dotenv

load_dotenv()

COM_PORT = os.environ.get("COM_PORT", "COM3")
BAUD_RATE = 9600
TCP_PORT = int(os.environ.get("BRIDGE_PORT", 5000))

class SerialBridge:
    def __init__(self):
        self.ser = None
        self.bt_connected = False
        self.state_lock = threading.Lock()
        self.tcp_clients = [] # Tracks active Docker connections

    def connect_serial(self):
        """Continuously hammers the COM port until it opens."""
        while True:
            with self.state_lock:
                if self.ser and self.ser.is_open:
                    try:
                        self.ser.close()
                    except Exception:
                        pass
            
            print(f"\n[WATCHDOG] Attempting to connect to {COM_PORT}...")
            try:
                # CRITICAL: timeout=0.1 forces the OS to check the hardware continuously.
                # write_timeout prevents the script from hanging if the buffer fills up.
                new_ser = serial.Serial(COM_PORT, BAUD_RATE, timeout=0.1, write_timeout=0.1)
                
                with self.state_lock:
                    self.ser = new_ser
                    self.bt_connected = True
                
                print(f"[WATCHDOG] Successfully connected to {COM_PORT}!\n")
                return # Break the loop, connection established
            except Exception as e:
                print(f"[WATCHDOG] Failed: {e}. Retrying in 2 seconds...")
                time.sleep(2)

    def trigger_reconnect(self):
        """Flags the connection as dead and blocks until reconnected."""
        with self.state_lock:
            if not self.bt_connected:
                return # Reconnect is already in progress
            self.bt_connected = False
            
        print("[WATCHDOG] Hardware disconnect detected. Triggering auto-recovery...")
        self.connect_serial()

    def disconnect_serial(self):
        """Handles manual #DISCONNECT command."""
        with self.state_lock:
            self.bt_connected = False
            if self.ser and self.ser.is_open:
                try:
                    self.ser.close()
                except Exception:
                    pass
        print("\n[WATCHDOG] Hardware manually disconnected via TCP command.\n")

    def serial_to_tcp_loop(self):
        """Dedicated thread: Reads from hardware, broadcasts to Docker."""
        while True:
            if not self.bt_connected:
                time.sleep(0.1)
                continue
            
            try:
                # By forcing a read() rather than checking in_waiting, 
                # we force the OS to throw an error if the BT module is turned off.
                bytes_to_read = max(1, self.ser.in_waiting)
                data = self.ser.read(bytes_to_read)
                
                if data:
                    # Broadcast to all connected clients
                    for conn in list(self.tcp_clients):
                        try:
                            conn.sendall(data)
                        except Exception:
                            # Safely check if it exists before removing
                            if conn in self.tcp_clients:
                                self.tcp_clients.remove(conn)
                            
            except Exception as e:
                print(f"[HARDWARE ERROR] Read failed: {e}")
                self.trigger_reconnect()

    def tcp_to_serial_loop(self, conn, addr):
        """Dedicated thread per Docker client: Reads from Docker, writes to hardware."""
        print(f"[{addr[0]}:{addr[1]}] Docker connected.")
        self.tcp_clients.append(conn)
        
        try:
            while True:
                data = conn.recv(1024)
                if not data:
                    break # Docker disconnected gracefully
                
                # Intercept explicit commands
                text_cmd = data.decode('utf-8', errors='ignore').strip()
                if text_cmd == "#RECONNECT":
                    self.trigger_reconnect()
                    continue
                elif text_cmd == "#DISCONNECT":
                    self.disconnect_serial()
                    continue

                # Forward normal data to hardware
                if self.bt_connected:
                    try:
                        with self.state_lock:
                            self.ser.write(data)
                            self.ser.flush() # CRITICAL: Forces OS to push data, instantly catching disconnects
                    except Exception as e:
                        print(f"[{addr[0]}] Write failed: {e}")
                        self.trigger_reconnect()
                else:
                    print(f"[{addr[0]}] Dropped instruction (Hardware offline).")
                    
        except Exception as e:
            print(f"[{addr[0]}] TCP Error: {e}")
        finally:
            print(f"[{addr[0]}] Docker disconnected.")
            if conn in self.tcp_clients:
                self.tcp_clients.remove(conn)
            conn.close()

    def start(self):
        # 1. Establish initial hardware connection
        self.connect_serial()
        
        # 2. Start the continuous hardware reading thread
        threading.Thread(target=self.serial_to_tcp_loop, daemon=True).start()

        # 3. Start the TCP Server
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('0.0.0.0', TCP_PORT))
        server.listen(5)
        print(f"Relay active. Listening on TCP port {TCP_PORT}...\n")

        try:
            # 4. Accept Docker connections indefinitely
            while True:
                conn, addr = server.accept()
                threading.Thread(target=self.tcp_to_serial_loop, args=(conn, addr), daemon=True).start()
        except KeyboardInterrupt:
            print("\nShutting down bridge...")
        finally:
            server.close()
            self.disconnect_serial()

if __name__ == "__main__":
    bridge = SerialBridge()
    bridge.start()