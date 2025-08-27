# Import necessary SimQN modules
from qns.simulator.simulator import Simulator
from qns.simulator.event import Event
from qns.entity.node.app import Application
from qns.entity.node.node import QNode
from qns.entity.cchannel.cchannel import ClassicChannel, ClassicPacket, RecvClassicPacket
from qns.simulator import func_to_event

# Import socket libraries for SCTP communication
from socket import AF_INET, socket
from sctp import sctpsocket_tcp
import select

# Define IP addresses and port numbers
CU_IP = "10.108.202.32"
DU_IP = "10.108.202.33"
TUNNEL_IP = "10.109.202.32"
SCTP_PORT = 38472
BUFFER_SIZE = 32768
#16384
# -----------------------------
# SETTING UP SCTP CONNECTIONS
# -----------------------------
# Create an SCTP Server Socket on the tunneling IP to receive connections from DU
server_socket = sctpsocket_tcp(AF_INET)
server_socket.bind((TUNNEL_IP, SCTP_PORT))
server_socket.listen(1)
du_conn, addr = server_socket.accept()
print(f"✅ Connected to DU at {addr}")

# Create an SCTP Client Socket to communicate with CU
cu_client_socket = sctpsocket_tcp(AF_INET)
cu_client_socket.connect((CU_IP, SCTP_PORT))
print("✅ Connected to CU")

# Perform handshake
du_conn.sendall(b"DU Handshake Init")
cu_client_socket.sendall(b"CU Handshake Init")

# -----------------------------
# CLASS: TunnelApp (Handles Event-Driven Packet Forwarding in SimQN)
# -----------------------------
class TunnelApp(Application):
    def __init__(self, dest: QNode, channel: ClassicChannel, is_qcu: bool):
        super().__init__()
        self.dest = dest
        self.channel = channel
        self.is_qcu = is_qcu  # True if this app is for QCU, False if for QDU
        self.add_handler(self.handle_recv_packet, [RecvClassicPacket], [])

    def install(self, node: QNode, simulator: Simulator):
        super().install(node, simulator)
        self.schedule_recv()

    def schedule_recv(self):
        """Schedules an event to check for SCTP data periodically."""
        t = self._simulator.current_time + self._simulator.time(sec=0.1)
        event = func_to_event(t, self.receive_sctp_data, by=self)
        self._simulator.add_event(event)

    def receive_sctp_data(self):
        """Handles non-blocking reception of SCTP data."""
        conn = cu_client_socket if self.is_qcu else du_conn
        ready, _, _ = select.select([conn], [], [], 0.1)  # Non-blocking check
        if ready:
            try:
                data = conn.recv(BUFFER_SIZE)
                if data:
                    print(f"📥 {self.get_node().name} received {len(data)} bytes, injecting into SimQN Tunnel")
                    self.send_packet(data)
            except Exception as e:
                print(f"❌ SCTP Error: {e}")

        self.schedule_recv()  # Keep polling

    def send_packet(self, data):
        """Sends raw data as a ClassicPacket through the SimQN tunnel."""
        packet = ClassicPacket(msg=data, src=self.get_node(), dest=self.dest)
        self.channel.send(packet=packet, next_hop=self.dest)

    def handle_recv_packet(self, node: QNode, event: Event):
        """Handles received packets and forwards them via SCTP."""
        if isinstance(event, RecvClassicPacket):
            packet = event.packet
            data = packet.get()
            print(f"🔄 [{self._simulator.current_time}] {self.get_node().name} received: {len(data)} bytes")

            # Forward to CU or DU
            self.forward_sctp(data)

    def forward_sctp(self, data):
        """Forwards data to CU or DU via SCTP."""
        conn = cu_client_socket if self.is_qcu else du_conn
        try:
            conn.send(data)
            print(f"📤 Forwarded {len(data)} bytes to {'CU' if self.is_qcu else 'DU'}")
        except Exception as e:
            print(f"❌ Error forwarding to {'CU' if self.is_qcu else 'DU'}: {e}")

# -----------------------------
# SETTING UP SimQN TUNNEL
# -----------------------------
qdu_node = QNode("QDU")  # Quantum DU node
qcu_node = QNode("QCU")  # Quantum CU node
simqn_channel = ClassicChannel(name="simqn_tunnel")

qdu_node.add_cchannel(simqn_channel)
qcu_node.add_cchannel(simqn_channel)

qdu_app = TunnelApp(dest=qcu_node, channel=simqn_channel, is_qcu=False)  # QDU forwards to CU
qcu_app = TunnelApp(dest=qdu_node, channel=simqn_channel, is_qcu=True)   # QCU forwards to DU

qdu_node.add_apps(qdu_app)
qcu_node.add_apps(qcu_app)

# -----------------------------
# INITIALIZE SimQN SIMULATION
# -----------------------------
sim = Simulator(0, 100, accuracy=10000)
qdu_node.install(sim)
qcu_node.install(sim)

# -----------------------------
# RUN SimQN SIMULATION
# -----------------------------
sim.run()
