from socket import AF_INET, socket
from sctp import sctpsocket_tcp
import threading
import time

# -----------------------------
# NETWORK CONFIGURATION
# -----------------------------

CU_IP = "10.108.202.32"
DU_IP = "10.108.202.33"
TUNNEL_IP = "10.109.202.32"
SCTP_PORT = 38472
BUFFER_SIZE = 128 * 10 ** 3

# DISTANCE SETTINGS
DISTANCE_KM = 20  # 20 km distance
LIGHT_SPEED = 200000000  # Speed in fiber optic (km/s)
DELAY_SEC = (DISTANCE_KM / LIGHT_SPEED)

# -----------------------------
# SCTP CONNECTIONS
# -----------------------------

def setup_sctp_connection():
    server_socket = sctpsocket_tcp(AF_INET)
    server_socket.bind((TUNNEL_IP, SCTP_PORT))
    server_socket.listen(1)
    du_conn, addr = server_socket.accept()
    print(f"✅ Connected to DU at {addr}")

    cu_client_socket = sctpsocket_tcp(AF_INET)
    cu_client_socket.connect((CU_IP, SCTP_PORT))
    print("✅ Connected to CU")
    
    return du_conn, cu_client_socket

# -----------------------------
# MESSAGE FORWARDING WITHOUT QuNetSim
# -----------------------------

def receive_and_forward(src_name, conn, forward_conn):
    while True:
        try:
            data = conn.recv(BUFFER_SIZE)
            if data:
                print(f"📥 {src_name} received {len(data)} bytes")
                
                # Simulate delay
                time.sleep(DELAY_SEC)
                
                # Forward through SCTP tunnel
                forward_conn.send(data)
                print(f"📤 {src_name} forwarded {len(data)} bytes with {DELAY_SEC:.12f}s delay")
        except Exception as e:
            print(f"⚠ Error: {e}")
            break

def main():
    du_conn, cu_client_socket = setup_sctp_connection()
    
    thread1 = threading.Thread(target=receive_and_forward, args=("DU", du_conn, cu_client_socket))
    thread2 = threading.Thread(target=receive_and_forward, args=("CU", cu_client_socket, du_conn))
    
    thread1.start()
    thread2.start()
    
    thread1.join()
    thread2.join()

if __name__ == "__main__":
    main()
