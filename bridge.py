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
import sys
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
        self.active_mode = True   # True = Keep alive. False = Intentionally offline.
        self.reconnecting = False # Prevents multiple hammer threads at once
        self.state_lock = threading.Lock()
        self.tcp_clients = []     # Tracks active Docker connections

    def connect_serial(self):
        """Continuously hammers the COM port until it opens or is manually aborted."""
        while True:
            with self.state_lock:
                if not self.reconnecting:
                    return # Abort the thread if a manual disconnect was called
                
                if self.ser and self.ser.is_open:
                    try:
                        self.ser.close()
                    except Exception:
                        pass
            
            try:
                new_ser = serial.Serial(COM_PORT, BAUD_RATE, timeout=0.1, write_timeout=0.1)
                
                with self.state_lock:
                    self.ser = new_ser
                    self.bt_connected = True
                    self.reconnecting = False # Hammering complete
                
                print(f"\n[WATCHDOG] Successfully connected to {COM_PORT}!")
                return 
            except Exception:
                time.sleep(2) # Fail silently in background to keep REPL clean, retry in 2s

    def trigger_reconnect(self, manual=False):
        """Spawns a reconnect thread if one isn't already active."""
        with self.state_lock:
            # If auto-recovery triggers but we wanted it disconnected, ignore it
            if not manual and not self.active_mode:
                return 

            if self.reconnecting:
                if manual:
                    print("\n[WATCHDOG] Reconnection already in progress.")
                return
            
            self.active_mode = True # Re-enable auto-recovery
            self.bt_connected = False
            self.reconnecting = True
            
        if manual:
            print(f"\n[WATCHDOG] Manual connection triggered for {COM_PORT}...")
        else:
            print("\n[WATCHDOG] Hardware disconnect detected. Triggering auto-recovery...")
            
        threading.Thread(target=self.connect_serial, daemon=True).start()

    def disconnect_serial(self):
        """Handles manual disconnect commands, halting auto-recovery."""
        with self.state_lock:
            self.active_mode = False  # Disable auto-recovery entirely
            self.reconnecting = False # Kill active hammering thread
            self.bt_connected = False
            if self.ser and self.ser.is_open:
                try:
                    self.ser.close()
                except Exception:
                    pass
        print(f"\n[WATCHDOG] Hardware manually disconnected from {COM_PORT}. Auto-recovery paused.")

    def serial_to_tcp_loop(self):
        """Dedicated thread: Reads from hardware, broadcasts to Docker."""
        while True:
            if not self.bt_connected:
                time.sleep(0.1)
                continue
            
            try:
                if not self.ser:
                    time.sleep(0.1)
                    continue
                    
                bytes_to_read = max(1, self.ser.in_waiting)
                data = self.ser.read(bytes_to_read)
                
                if data:
                    for conn in list(self.tcp_clients):
                        try:
                            conn.sendall(data)
                        except Exception:
                            if conn in self.tcp_clients:
                                self.tcp_clients.remove(conn)
                                
            except Exception as e:
                # Only log and trigger auto-recovery if we didn't intentionally disconnect
                with self.state_lock:
                    if self.bt_connected:
                        print(f"\n[HARDWARE ERROR] Read failed: {e}")
                        self.trigger_reconnect()

    def tcp_to_serial_loop(self, conn, addr):
        """Dedicated thread per Docker client: Reads from Docker, writes to hardware."""
        print(f"\n[{addr[0]}:{addr[1]}] Docker connected.")
        self.tcp_clients.append(conn)
        
        try:
            while True:
                data = conn.recv(1024)
                if not data:
                    break
                
                # Intercept explicit TCP commands
                text_cmd = data.decode('utf-8', errors='ignore').strip()
                if text_cmd == "#RECONNECT":
                    self.trigger_reconnect(manual=True)
                    continue
                elif text_cmd == "#DISCONNECT":
                    self.disconnect_serial()
                    continue

                # Forward normal data
                if self.bt_connected:
                    try:
                        with self.state_lock:
                            self.ser.write(data)
                            self.ser.flush()
                    except Exception as e:
                        print(f"\n[{addr[0]}] Write failed: {e}")
                        self.trigger_reconnect()
                else:
                    print(f"\n[{addr[0]}] Dropped instruction (Hardware offline).")
                    
        except Exception as e:
            print(f"\n[{addr[0]}] TCP Error: {e}")
        finally:
            print(f"\n[{addr[0]}] Docker disconnected.")
            if conn in self.tcp_clients:
                self.tcp_clients.remove(conn)
            conn.close()

    def start_tcp_server(self):
        """Dedicated thread: Accepts incoming Docker connections."""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('0.0.0.0', TCP_PORT))
        server.listen(5)
        print(f"[TCP] Relay active. Listening on port {TCP_PORT}...")

        while True:
            try:
                conn, addr = server.accept()
                threading.Thread(target=self.tcp_to_serial_loop, args=(conn, addr), daemon=True).start()
            except Exception as e:
                print(f"[TCP] Server error: {e}")
                break

    def repl(self):
        """Main thread: Provides an interactive command-line interface."""
        print("\n=== Serial Bridge REPL ===")
        print("Commands: connect, disconnect, status, clear, exit")
        print("==========================\n")
        
        while True:
            try:
                cmd = input("bridge> ").strip().lower()
                if not cmd:
                    continue
                
                if cmd in ['exit', 'quit']:
                    print("Shutting down bridge...")
                    self.disconnect_serial()
                    os._exit(0) # Forcefully kill all daemon threads immediately
                
                elif cmd == 'disconnect':
                    self.disconnect_serial()
                    
                elif cmd in ['connect', 'reconnect']:
                    self.trigger_reconnect(manual=True)
                    
                elif cmd == 'status':
                    status = "CONNECTED" if self.bt_connected else ("DISCONNECTED" if not self.active_mode else "ERROR")
                    reconnecting = " (Reconnecting...)" if self.reconnecting else ""
                    print(f"Hardware Status: {status}{reconnecting}")
                    print(f"Active TCP Clients: {len(self.tcp_clients)}")
                    
                elif cmd == 'clear':
                    os.system('cls' if os.name == 'nt' else 'clear')
                    
                else:
                    print("Unknown command. Available: connect, disconnect, status, clear, exit")
                    
            except KeyboardInterrupt:
                print("\nShutting down bridge...")
                self.disconnect_serial()
                os._exit(0)
            except EOFError:
                break

    def start(self):
        # 1. Start continuous hardware reading thread
        threading.Thread(target=self.serial_to_tcp_loop, daemon=True).start()

        # 2. Start TCP Server thread
        threading.Thread(target=self.start_tcp_server, daemon=True).start()

        # 3. Establish initial hardware connection (Non-blocking)
        self.trigger_reconnect(manual=True)

        # 4. Take over main thread with the REPL
        time.sleep(0.5) # Give startup prints a half-second to clear out
        self.repl()

if __name__ == "__main__":
    bridge = SerialBridge()
    bridge.start()
