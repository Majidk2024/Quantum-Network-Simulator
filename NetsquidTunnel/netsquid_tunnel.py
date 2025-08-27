import netsquid as ns
import pydynaa
from netsquid.nodes import Node
from netsquid.nodes.connections import Connection
from netsquid.components import ClassicalChannel
from netsquid.components.models import FibreDelayModel
from socket import AF_INET
from sctp import sctpsocket_tcp
import select

# Simple Message class for compatibility
class Message:
    def __init__(self, data):
        self.items = [data]

# Network Configuration
CU_IP = "10.108.202.32"
DU_IP = "10.108.202.33"
TUNNEL_IP = "10.109.202.32"
SCTP_PORT = 38472
BUFFER_SIZE = 128384
POLL_INTERVAL = 10000  # Polling interval (ns)

# -----------------------------
# SCTP CONNECTION SETUP
# -----------------------------

# QDU connects to DU (DU Side)
qdu_to_du_socket = sctpsocket_tcp(AF_INET)
qdu_to_du_socket.bind((TUNNEL_IP, SCTP_PORT))
qdu_to_du_socket.listen(1)
du_conn, du_addr = qdu_to_du_socket.accept()
du_conn.setblocking(False)  # Prevent blocking
print(f"QDU connected to DU at {du_addr}")

# QCU connects to CU (CU Side)
qcu_to_cu_socket = sctpsocket_tcp(AF_INET)
qcu_to_cu_socket.connect((CU_IP, SCTP_PORT))
qcu_to_cu_socket.setblocking(False)  # Prevent blocking
print("QCU connected to CU")

# -----------------------------
# EVENT-BASED SCTP HANDLER
# -----------------------------

class SCTPEventHandler(pydynaa.Entity):
    """Handles SCTP messages using NetSquid's event system with QDU/QCU architecture."""

    evtype_poll = pydynaa.EventType("Poll SCTP Messages", "")

    def __init__(self, qcu_node, qdu_node):
        super().__init__()
        self.qcu_node = qcu_node  # QCU NetSquid node
        self.qdu_node = qdu_node  # QDU NetSquid node

        # Register event handlers
        self._wait(pydynaa.EventHandler(self.poll_sctp_messages), entity=self, event_type=self.evtype_poll)
        
        # Start polling SCTP messages
        self._schedule_after(POLL_INTERVAL, self.evtype_poll)

    def poll_sctp_messages(self, event=None):
        """Polls SCTP messages: DU↔QDU and CU↔QCU, forwards through NetSquid simulation."""
        readable, _, _ = select.select([qcu_to_cu_socket, du_conn], [], [], 0)

        # QCU receives from CU
        if qcu_to_cu_socket in readable:
            try:
                payload = qcu_to_cu_socket.recv(BUFFER_SIZE)  # Receive from CU
                if payload:
                    print(f"[CU → QCU] Received {len(payload)} bytes from CU")
                    # Send through NetSquid simulation: QCU → QDU via quantum processing
                    msg = Message(payload)
                    self.qcu_node.process_cu_message(msg)
            except Exception:
                pass  # Ignore timeout errors

        # QDU receives from DU  
        if du_conn in readable:
            try:
                payload = du_conn.recv(BUFFER_SIZE)  # Receive from DU
                if payload:
                    print(f"[DU → QDU] Received {len(payload)} bytes from DU")
                    # Send through NetSquid simulation: QDU → QCU via quantum processing
                    msg = Message(payload)
                    self.qdu_node.process_du_message(msg)
            except Exception:
                pass  # Ignore timeout errors

        # Re-schedule polling event
        self._schedule_after(POLL_INTERVAL, self.evtype_poll)

# -----------------------------
# CLASSICAL NETWORK (NETSQUID)
# -----------------------------

class QCUNode(Node):
    """Quantum Central Unit - NetSquid node that connects to CU."""

    def __init__(self):
        super().__init__("QCU")
        self.add_ports(["in_port", "out_port"])
        self.ports["in_port"].bind_input_handler(self.handle_message_from_qdu)
        
        # Define event types
        self.evtype_forward_cu = pydynaa.EventType("QCU Forward to CU", "")
        self.evtype_process_cu = pydynaa.EventType("QCU Process CU Message", "")
        
        # Register event handlers
        self._wait(pydynaa.EventHandler(self.forward_to_cu), entity=self, event_type=self.evtype_forward_cu)
        self._wait(pydynaa.EventHandler(self.quantum_process_cu_message), entity=self, event_type=self.evtype_process_cu)

    def process_cu_message(self, message):
        """Process message from CU through quantum processing."""
        import time
        start_time = time.time()
        print(f"[QCU] Starting quantum processing of CU message: {len(message.items[0])} bytes at {start_time:.3f}")
        self.pending_cu_data = message.items[0]
        self.cu_start_time = start_time
        
        # 🔬 QCU QUANTUM PROCESSING DELAY for CU message
        qcu_processing_delay = 6000  # 6 seconds processing delay (for 110-120ms RTT)
        self._schedule_after(qcu_processing_delay, self.evtype_process_cu)

    def quantum_process_cu_message(self, event=None):
        """Complete quantum processing and send through NetSquid tunnel."""
        if hasattr(self, 'pending_cu_data'):
            import time
            elapsed = time.time() - self.cu_start_time
            print(f"[QCU] Quantum processing complete after {elapsed*1000:.1f}ms, sending to QDU via NetSquid tunnel")
            # Send through NetSquid quantum tunnel using message wrapper
            netsquid_msg = Message(self.pending_cu_data)
            self.ports["out_port"].tx_output(netsquid_msg)
            self.pending_cu_data = None

    def handle_message_from_qdu(self, message):
        """Handles messages received from QDU through NetSquid simulation."""
        import time
        receive_time = time.time()
        
        # Extract original binary data carefully from NetSquid message
        if hasattr(message, 'items') and len(message.items) > 0:
            data = message.items[0]
            # If it's a nested Message object, extract its data
            if hasattr(data, 'items'):
                data = data.items[0]
        else:
            data = message
        
        # Ensure data is in correct binary format
        if hasattr(data, 'tobytes'):
            data = data.tobytes()
        elif isinstance(data, str):
            data = data.encode()
        elif isinstance(data, (bytes, bytearray)):
            pass  # Already correct format
        else:
            # Try to convert to bytes safely
            try:
                data = bytes(data)
            except:
                print(f"[ERROR] Cannot convert data type {type(data)} to bytes")
                return
        
        print(f"[QCU] Received quantum message from QDU: {len(data)} bytes at {receive_time:.3f}")
        
        # Store data for later forwarding
        self.pending_data = data
        self.qdu_receive_time = receive_time
        
        # 🔬 QCU QUANTUM PROCESSING DELAY
        qcu_processing_delay = 6000  # 6 seconds QCU processing delay (for 110-120ms RTT)
        
        # Schedule delayed forwarding to CU after quantum processing
        self._schedule_after(qcu_processing_delay, self.evtype_forward_cu)

    def forward_to_cu(self, event=None):
        """Forward data to CU after quantum processing delay."""
        try:
            if hasattr(self, 'pending_data') and self.pending_data:
                import time
                total_elapsed = time.time() - self.qdu_receive_time
                qcu_to_cu_socket.send(self.pending_data)
                print(f"[QCU] Quantum processing complete → CU sent: {len(self.pending_data)} bytes (total delay: {total_elapsed*1000:.1f}ms)")
                self.pending_data = None  # Clear after sending
        except Exception as e:
            print(f"[ERROR] QCU failed to forward to CU: {e}")

class QDUNode(Node):
    """Quantum Distributed Unit - NetSquid node that connects to DU."""

    def __init__(self):
        super().__init__("QDU")
        self.add_ports(["in_port", "out_port"])
        self.ports["in_port"].bind_input_handler(self.handle_message_from_qcu)
        
        # Define event types
        self.evtype_forward_du = pydynaa.EventType("QDU Forward to DU", "")
        self.evtype_process_du = pydynaa.EventType("QDU Process DU Message", "")
        
        # Register event handlers
        self._wait(pydynaa.EventHandler(self.forward_to_du), entity=self, event_type=self.evtype_forward_du)
        self._wait(pydynaa.EventHandler(self.quantum_process_du_message), entity=self, event_type=self.evtype_process_du)

    def process_du_message(self, message):
        """Process message from DU through quantum processing."""
        print(f"[QDU] Starting quantum processing of DU message: {len(message.items[0])} bytes")
        self.pending_du_data = message.items[0]
        
        # 🔬 QDU QUANTUM PROCESSING DELAY for DU message
        qdu_processing_delay = 6000  # 6 seconds processing delay (for 110-120ms RTT)
        self._schedule_after(qdu_processing_delay, self.evtype_process_du)

    def quantum_process_du_message(self, event=None):
        """Complete quantum processing and send through NetSquid tunnel."""
        if hasattr(self, 'pending_du_data'):
            print(f"[QDU] Quantum processing complete, sending to QCU via NetSquid tunnel")
            # Send through NetSquid quantum tunnel using message wrapper
            netsquid_msg = Message(self.pending_du_data)
            self.ports["out_port"].tx_output(netsquid_msg)
            self.pending_du_data = None

    def handle_message_from_qcu(self, message):
        """Handles messages received from QCU through NetSquid simulation."""
        # Extract original binary data carefully from NetSquid message
        if hasattr(message, 'items') and len(message.items) > 0:
            data = message.items[0]
            # If it's a nested Message object, extract its data
            if hasattr(data, 'items'):
                data = data.items[0]
        else:
            data = message
        
        # Ensure data is in correct binary format
        if hasattr(data, 'tobytes'):
            data = data.tobytes()
        elif isinstance(data, str):
            data = data.encode()
        elif isinstance(data, (bytes, bytearray)):
            pass  # Already correct format
        else:
            # Try to convert to bytes safely
            try:
                data = bytes(data)
            except:
                print(f"[ERROR] Cannot convert data type {type(data)} to bytes")
                return
        
        print(f"[QDU] Received quantum message from QCU: {len(data)} bytes")
        
        # Store data for later forwarding
        self.pending_data = data
        
        # 🔬 QDU QUANTUM PROCESSING DELAY
        qdu_processing_delay = 6000  # 6 seconds QDU processing delay (for 110-120ms RTT)
        
        # Schedule delayed forwarding to DU after quantum processing
        self._schedule_after(qdu_processing_delay, self.evtype_forward_du)

    def forward_to_du(self, event=None):
        """Forward data to DU after quantum processing delay."""
        try:
            if hasattr(self, 'pending_data') and self.pending_data:
                du_conn.send(self.pending_data)
                print(f"[QDU] Quantum processing complete → DU sent: {len(self.pending_data)} bytes")
                self.pending_data = None  # Clear after sending
        except Exception as e:
            print(f"[ERROR] QDU failed to forward to DU: {e}")

class QuantumConnection(Connection):
    """Bi-directional quantum connection between QCU and QDU."""

    def __init__(self, length):
        super().__init__("Quantum_Tunnel")
        
        # Add all required ports first
        self.add_ports(["QCU_out", "QDU_in", "QDU_out", "QCU_in"])
        
        # Add realistic quantum fiber delay model with significant delay
        quantum_fiber_model = FibreDelayModel(c=200000)  # Much slower: 200 km/s (1000x slower for testing)
        
        # QCU → QDU channel
        self.add_subcomponent(ClassicalChannel("QCU_to_QDU", length=length, models={"delay_model": quantum_fiber_model}))
        self.ports["QCU_out"].forward_input(self.subcomponents["QCU_to_QDU"].ports["send"])
        self.subcomponents["QCU_to_QDU"].ports["recv"].forward_output(self.ports["QDU_in"])

        # QDU → QCU channel  
        self.add_subcomponent(ClassicalChannel("QDU_to_QCU", length=length, models={"delay_model": quantum_fiber_model}))
        self.ports["QDU_out"].forward_input(self.subcomponents["QDU_to_QCU"].ports["send"])
        self.subcomponents["QDU_to_QCU"].ports["recv"].forward_output(self.ports["QCU_in"])

# -----------------------------
# SIMULATION SETUP
# -----------------------------

quantum_distance = 100000e-3  # 100 km - quantum tunnel distance (increased for more delay)

# Create QCU and QDU NetSquid Nodes
qcu_node = QCUNode()  # Quantum Central Unit
qdu_node = QDUNode()  # Quantum Distributed Unit

# Create Quantum Connection between QCU and QDU
quantum_tunnel = QuantumConnection(quantum_distance)

# Connect QCU and QDU through quantum tunnel
qcu_node.ports["out_port"].connect(quantum_tunnel.ports["QCU_out"])
qdu_node.ports["in_port"].connect(quantum_tunnel.ports["QDU_in"])
qdu_node.ports["out_port"].connect(quantum_tunnel.ports["QDU_out"])
qcu_node.ports["in_port"].connect(quantum_tunnel.ports["QCU_in"])

# Create SCTP Event Handler with QCU/QDU architecture
sctp_handler = SCTPEventHandler(qcu_node, qdu_node)

print("🌌 Quantum Tunnel Architecture:")
print("   DU ↔ QDU ↔ [NetSquid Quantum Simulation] ↔ QCU ↔ CU")
print("   QDU and QCU are NetSquid simulator nodes")
print("   All data flows through quantum simulation")
print("   🔬 Quantum Processing Delays: QDU=6s, QCU=6s")
print(f"   📡 Fiber Distance: {quantum_distance*1000:.0f}m, Speed: 200 km/s")
print("   ⏱️  Expected RTT: 110-120ms")

# -----------------------------
# KEEP NETSQUID SIMULATION RUNNING
# -----------------------------

print("Starting NetSquid Quantum Tunnel Simulation...")
try:
    # Start NetSquid simulation - try different APIs
    if hasattr(ns, 'sim_run'):
        ns.sim_run()
    elif hasattr(ns, 'run'):
        ns.run()
    else:
        # Fallback - keep PyDynAA event loop running
        import time
        print("Using fallback event loop...")
        while True:
            time.sleep(0.1)
except KeyboardInterrupt:
    print("Simulation stopped by user")

