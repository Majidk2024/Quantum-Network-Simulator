import socket
import sctp

# SCTP Tunnel Info
SCTP_IP = "10.109.202.32"  # Tunnel IP
DU_IP = "10.108.202.33"  # DU Machine IP
SCTP_PORT = 38472  # SCTP Port
BUFFER_SIZE =  4096 #changing the buffer size since error was there before

# Set up SCTP listener on DU
server_socket = sctp.sctpsocket_tcp(socket.AF_INET)
server_socket.bind((DU_IP, SCTP_PORT))
server_socket.listen(1)
print(f"DU listening on {DU_IP}:{SCTP_PORT}...")
conn, addr = server_socket.accept()
print(f"Connected to CU: {addr}")
while True:
    try:
        data = conn.recv(BUFFER_SIZE)
        if not data:
            print("CU closed the connection.")
            break
        print(f"Received {len(data)} bytes from CU. Forwarding back...")
        conn.send(data)
    except ConnectionResetError:
        print("Connection reset by tunnel. Waiting for reconnection...")
        conn.close()
        conn, addr = server_socket.accept()
        print(f"Reconnected to CU: {addr}")

