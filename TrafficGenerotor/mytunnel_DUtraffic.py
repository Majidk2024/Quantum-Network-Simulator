import socket
import time
import random
import sctp
import statistics

# -------------------
# Configuration
# -------------------

SCTP_IP = "10.109.202.32"  # Tunnel IP (CU)
DU_IP = "10.108.202.33"     # DU Machine IP
SCTP_PORT = 38472           # SCTP Tunnel Port

NUM_PACKETS = 11
BUFFER_SIZE = 65536
#128*1024
#65536
RETRY_DELAY = 2  # Seconds before retrying connection

rtt_list = []
jitter_list = []
mismatched_packets = 0  # Count packets where received data ≠ sent data
total_bytes_sent = 0
total_bytes_received = 0

# -------------------
# Utility Functions
# -------------------

def make_random_msg():
    """Generate a random binary message (8 to 300 bytes)."""
    #nbytes = random.randint(8, 300)
    nbytes = 1024
    return bytearray(random.getrandbits(8) for _ in range(nbytes))


def connect_to_du():
    """Attempts to establish an SCTP connection to DU with automatic retries."""
    while True:
        try:
            sock = sctp.sctpsocket_tcp(socket.AF_INET)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)  # Enable keep-alive
            sock.connect((SCTP_IP, SCTP_PORT))
            print(f"[INFO] Connected to DU at {DU_IP}:{SCTP_PORT}")
            return sock
        except Exception as e:
            print(f"[ERROR] Failed to connect to DU. Retrying in {RETRY_DELAY}s... Error: {e}")
            time.sleep(RETRY_DELAY)


def send_sctp_packet(sock, message):
    """Send an SCTP packet and check if received data matches the sent message."""
    global total_bytes_sent, total_bytes_received, mismatched_packets

    # Ensure message is bytes (skip encoding if it's already bytes or bytearray)
    if isinstance(message, str):
        message = message.encode()
    elif isinstance(message, bytearray):
        message = bytes(message)  # Convert bytearray to bytes

    start_time = time.time()

    try:
        # Send packet with ppid:0 and stream=0 for consistency
        sock.sendall(message)
        total_bytes_sent += len(message)

        # Receive response
        data = sock.recv(BUFFER_SIZE)

        if not data:
            print("[WARNING] No response received!")
            mismatched_packets += 1
            return None, False

        total_bytes_received += len(data)

        if len(data) < len(message):  # Partial packet received
            print(f"[WARNING] Partial packet received! Sent {len(message)} bytes, got {len(data)} bytes.")
            mismatched_packets += 1
        elif data != message:  # Corrupted data check
            print(f"[WARNING] Data mismatch! Sent {len(message)} bytes, received {len(data)} bytes.")
            mismatched_packets += 1

    except (ConnectionResetError, BrokenPipeError):
        print("[WARNING] Connection lost. Reconnecting...")
        return None, True  # Indicate need for reconnection
    except Exception as e:
        print(f"[ERROR] Unexpected error while sending packet: {e}")
        return None, True  # Handle generic error

    end_time = time.time()
    return (end_time - start_time) * 1000, False  # Convert time to milliseconds


# -------------------
# Main Function
# -------------------

def evaluate_tunnel():
    global rtt_list, jitter_list, mismatched_packets, NUM_PACKETS

    sock = connect_to_du()  # Establish initial connection
    print(f"[INFO] Evaluating SCTP Tunnel to {DU_IP}:{SCTP_PORT}...\n")

    prev_rtt = None  # For jitter calculation

    for i in range(NUM_PACKETS):
        message = make_random_msg()
        rtt, should_reconnect = send_sctp_packet(sock, message)

        if should_reconnect:
            sock = connect_to_du()  # Reconnect if needed
            continue

        if rtt is not None:
            rtt_list.append(rtt)
            print(f"Packet {i + 1}: RTT = {rtt:.3f} ms")

            if prev_rtt is not None:
                jitter = abs(rtt - prev_rtt)
                jitter_list.append(jitter)
            prev_rtt = rtt
        else:
            print(f"Packet {i + 1} failed due to connection issues.")

    # Compute tunnel metrics only if valid RTTs exist
    if rtt_list:
        NUM_PACKETS = 10
        first_rtt = rtt_list[0]
        min_rtt = min(rtt_list)
        max_rtt = max(rtt_list)
        avg_rtt = sum(rtt_list[1:]) / (len(rtt_list) -  1)
        #jitter_avg = sum(jitter_list[1:]) / (len(jitter_list) - 1) if jitter_list else 0
        jitter_std = statistics.stdev(rtt_list[1:])  # exclude first
        mismatch_rate = (mismatched_packets / NUM_PACKETS) * 100
        throughput = (total_bytes_received * 8) / (sum(rtt_list[1:]) / 1000)  # bits per second
        new_throughput = throughput / 1000000  # Convert to Mbps

        print("\n=== Tunnel Performance Metrics ===")
        print(f"First Packet RTT  : {first_rtt:.3f} ms")
        print(f"Minimum RTT       : {min_rtt:.3f} ms")
        print(f"Maximum RTT       : {max_rtt:.3f} ms")
        print(f"Average RTT       : {avg_rtt:.3f} ms")
        print(f"Jitter (Avg)      : {jitter_std:.3f} ms")
        print(f"Mismatch Rate     : {mismatch_rate:.2f} %")
        print(f"Throughput_per_packet: {new_throughput:.8f} Mbps")
        print("===================================")
    else:
        print("No valid RTT measurements due to connection resets.")


if __name__ == "__main__":
    evaluate_tunnel()
