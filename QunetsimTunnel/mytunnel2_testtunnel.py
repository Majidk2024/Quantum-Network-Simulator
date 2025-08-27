from qunetsim.components.network import Network
from qunetsim.objects import Logger
from qunetsim.components import Host
from qunetsim.components import protocols
from qunetsim.utils.constants import Constants

from socket import AF_INET, socket
from sctp import sctpsocket_tcp

from collections.abc import Callable
from threading import Thread

Logger.DISABLED = True


class HostMod(Host):
    def __init__(self, host_id, processing_function: Callable, backend=None):
        super().__init__(host_id, backend)
        self._socket = socket
        self._processing_func = processing_function

    def _process_packet(self, packet):
        print("Entering _process_packet")
        msg = protocols.process(packet)

        if msg is None:
            print("Got no message to process!!!")
            return

        if msg.content == Constants.ACK:
            if packet:
                return super()._process_packet(packet)

        print(f"Processing packet from {msg.sender} to {self.host_id}: {msg.content}")

        # Process only if the packet is entering the tunnel
        if (self.host_id == "CU" and msg.sender == "DU") or (self.host_id == "DU" and msg.sender == "CU"):
            content = msg.content
            self._processing_func(content)
            print("Packet processed inside tunnel. Exiting processing.")
        else:
            print("Packet has exited the tunnel. Stopping processing.")


# -------------------
# Classical Network
# -------------------

IP = "10.109.202.32"
CU_IP = "10.108.202.32"
SCTP_PORT = 38472
DU_IP = "10.108.202.33"
server_socket: socket = sctpsocket_tcp(AF_INET)
server_socket.bind((IP, SCTP_PORT))
server_socket.listen(1)
du_conn, addr = server_socket.accept()
print(addr)
print("Connected to DU")

cu_client_socket: socket = sctpsocket_tcp(AF_INET)
cu_client_socket.connect((DU_IP, SCTP_PORT))
print("Connected to CU")


# -------------------
# Processing Functions
# -------------------

def qcu_to_cu(content):
    print("Sending packet to CU")
    du_conn.sendall(content)

def qdu_to_du(content):
    print("Sending packet to DU")
    cu_client_socket.sendall(content)


# -------------------
# Quantum Network
# -------------------

q_network = Network.get_instance()
q_nodes = ["CU", "DU"]
q_network.start(q_nodes)

q_cu_host = HostMod("CU", qcu_to_cu)
q_du_host = HostMod("DU", qdu_to_du)

q_cu_host.add_connection("DU")
q_du_host.add_connection("CU")

q_cu_host.start()
q_du_host.start()

q_network.add_hosts([q_cu_host, q_du_host])
print("Established quantum link between CU-Gw and DU-Gw")


# -------------------
# Handlers
# -------------------

BUFFER_SIZE = 65536

def handle_du():
    while True:
        payload = du_conn.recv(BUFFER_SIZE)
        q_du_host.send_classical("CU", payload, True)

def handle_cu():
    while True:
        payload = cu_client_socket.recv(BUFFER_SIZE)
        q_cu_host.send_classical("DU", payload, True)


# -------------------
# Threads
# -------------------

Thread(target=handle_du, args=()).start()
Thread(target=handle_cu, args=()).start()
