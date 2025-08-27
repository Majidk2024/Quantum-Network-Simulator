#!/usr/bin/env python3
"""
SeQUeNCe Quantum Tunnel Implementation
Implements ORAN CU-DU communication through SeQUeNCe quantum network simulation
"""

from sequence.kernel.event import Event
from sequence.kernel.process import Process
from sequence.kernel.timeline import Timeline
from sequence.kernel.entity import Entity
from sctp import sctpsocket_tcp
from socket import AF_INET
import select
import threading
import time
import logging

# Network Configuration
CU_IP = "10.108.202.32"
DU_IP = "10.108.202.33"
TUNNEL_IP = "10.109.202.32"
SCTP_PORT = 38472
BUFFER_SIZE = 16384

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Global variables
du_conn = None
cu_client_socket = None
timeline = None
qcu_node = None
qdu_node = None
simulation_running = False

class SCTPQuantumNode(Entity):
    """SeQUeNCe Entity for SCTP quantum tunnel"""
    
    def __init__(self, name, timeline, node_type):
        super().__init__(name, timeline)
        self.node_type = node_type  # "QCU" or "QDU"
        self.packets_sent = 0
        self.packets_received = 0
        self.partner_node = None
        self.message_queue = []

    def init(self):
        """Initialize the node - required abstract method implementation"""
        logger.info(f"Initializing {self.node_type} node: {self.name}")

    def set_partner(self, partner):
        """Set the quantum partner node"""
        self.partner_node = partner

    def send_quantum_message(self, data):
        """Send message through quantum simulation to partner"""
        if self.partner_node:
            # Schedule delivery with quantum delay (1ms = 1e6 nanoseconds)
            delivery_time = self.timeline.now() + 1e6
            
            # Create delivery process using correct SeQUeNCe API
            process = Process(self.partner_node, "receive_quantum_message", [data])
            event = Event(delivery_time, process)
            self.timeline.schedule(event)
            
            self.packets_sent += 1
            logger.info(f"🌌 [{self.name}] Scheduled quantum message delivery to {self.partner_node.name} at time {delivery_time}")

    def receive_quantum_message(self, data):
        """Receive message from quantum partner"""
        self.packets_received += 1
        logger.info(f"🌌 [{self.name}] Received quantum message: {len(data)} bytes at time {self.timeline.now()}")
        
        # Forward to SCTP based on node type
        if self.node_type == "QDU":
            # QDU forwards to DU
            forward_to_du(data)
        elif self.node_type == "QCU":
            # QCU forwards to CU
            forward_to_cu(data)

def setup_sctp_connections():
    """Setup SCTP connections for CU and DU"""
    global du_conn, cu_client_socket
    
    logger.info("Setting up SCTP connections...")
    
    # QDU server socket for DU connection
    qdu_server = sctpsocket_tcp(AF_INET)
    qdu_server.setsockopt(1, 2, 1)  # SO_REUSEADDR
    qdu_server.bind((TUNNEL_IP, SCTP_PORT))
    qdu_server.listen(1)
    logger.info(f"QDU listening for DU connection at {TUNNEL_IP}:{SCTP_PORT}")
    
    # Accept DU connection
    du_conn, du_addr = qdu_server.accept()
    du_conn.setblocking(False)
    logger.info(f"DU connected from {du_addr}")
    
    # QCU client socket to CU
    cu_client_socket = sctpsocket_tcp(AF_INET)
    cu_client_socket.connect((CU_IP, SCTP_PORT))
    cu_client_socket.setblocking(False)
    logger.info(f"QCU connected to CU at {CU_IP}:{SCTP_PORT}")
    
    logger.info("✅ SCTP connections established")

def forward_to_du(data):
    """Forward data to DU via SCTP"""
    global du_conn
    if du_conn:
        try:
            du_conn.send(data)
            logger.info(f"📤 [QDU → DU] Forwarded {len(data)} bytes")
        except Exception as e:
            logger.error(f"Error forwarding to DU: {e}")

def forward_to_cu(data):
    """Forward data to CU via SCTP"""
    global cu_client_socket
    if cu_client_socket:
        try:
            cu_client_socket.send(data)
            logger.info(f"📤 [QCU → CU] Forwarded {len(data)} bytes")
        except Exception as e:
            logger.error(f"Error forwarding to CU: {e}")

def handle_sctp_data():
    """Handle SCTP data from CU and DU"""
    global du_conn, cu_client_socket, qcu_node, qdu_node, simulation_running
    
    logger.info("Starting SCTP data handler...")
    
    while simulation_running:
        try:
            # Check for data from DU
            if du_conn:
                ready, _, _ = select.select([du_conn], [], [], 0.01)
                if ready:
                    try:
                        data = du_conn.recv(BUFFER_SIZE)
                        if data:
                            logger.info(f"📨 [DU → QDU] Received {len(data)} bytes")
                            # Send through quantum simulation
                            qdu_node.send_quantum_message(data)
                    except Exception as e:
                        if "Resource temporarily unavailable" not in str(e):
                            logger.error(f"Error reading from DU: {e}")
            
            # Check for data from CU
            if cu_client_socket:
                ready, _, _ = select.select([cu_client_socket], [], [], 0.01)
                if ready:
                    try:
                        data = cu_client_socket.recv(BUFFER_SIZE)
                        if data:
                            logger.info(f"📨 [CU → QCU] Received {len(data)} bytes")
                            # Send through quantum simulation
                            qcu_node.send_quantum_message(data)
                    except Exception as e:
                        if "Resource temporarily unavailable" not in str(e):
                            logger.error(f"Error reading from CU: {e}")
            
            time.sleep(0.001)  # Small delay to prevent busy waiting
            
        except Exception as e:
            logger.error(f"SCTP handler error: {e}")
            break

def run_sequence_simulation():
    """Run SeQUeNCe simulation continuously"""
    global timeline, simulation_running
    
    logger.info("🚀 Starting SeQUeNCe simulation engine...")
    
    while simulation_running:
        try:
            # Process events in timeline - use correct SeQUeNCe API
            if timeline.events:
                # Run next event
                timeline.run()
                logger.debug(f"⚡ Processed SeQUeNCe event at time {timeline.now()}")
            else:
                # No events, advance time slightly
                time.sleep(0.001)
        except Exception as e:
            logger.error(f"SeQUeNCe simulation error: {e}")
            break

def main():
    """Main function to setup and run the quantum tunnel"""
    global timeline, qcu_node, qdu_node, simulation_running
    
    logger.info("🌌" + "="*60)
    logger.info("🌌 STARTING SEQUENCE QUANTUM TUNNEL")
    logger.info("🌌" + "="*60)
    logger.info("🌌 Architecture: CU ↔ QCU ↔ [SeQUeNCe Quantum] ↔ QDU ↔ DU")
    logger.info("🌌" + "="*60)
    
    # Create SeQUeNCe timeline
    timeline = Timeline()
    
    # Create quantum nodes using Entity
    qcu_node = SCTPQuantumNode("QCU", timeline, "QCU")
    qdu_node = SCTPQuantumNode("QDU", timeline, "QDU")
    
    # Initialize nodes
    qcu_node.init()
    qdu_node.init()
    
    logger.info("✅ SeQUeNCe quantum nodes created")
    
    # Set partners for direct quantum communication
    qcu_node.set_partner(qdu_node)
    qdu_node.set_partner(qcu_node)
    
    logger.info("🌌 Quantum tunnel established between QCU and QDU (1ms delay)")
    
    # Setup SCTP connections
    setup_sctp_connections()
    
    # Start simulation
    simulation_running = True
    
    logger.info("🚀 Starting quantum tunnel bridge...")
    
    # Start SCTP data handler thread
    sctp_thread = threading.Thread(target=handle_sctp_data, daemon=True)
    sctp_thread.start()
    
    # Start SeQUeNCe simulation thread
    sim_thread = threading.Thread(target=run_sequence_simulation, daemon=True)
    sim_thread.start()
    
    logger.info("✅ All threads started - Quantum tunnel is ACTIVE")
    logger.info("📡 Ready to relay CU ↔ QCU ↔ QDU ↔ DU traffic")
    logger.info("Press Ctrl+C to stop")
    
    try:
        while True:
            time.sleep(5)
            # Log statistics every 5 seconds
            if qcu_node.packets_sent > 0 or qdu_node.packets_sent > 0:
                logger.info(f"📊 QCU: sent={qcu_node.packets_sent}, received={qcu_node.packets_received}")
                logger.info(f"📊 QDU: sent={qdu_node.packets_sent}, received={qdu_node.packets_received}")
                logger.info(f"📊 Timeline: current_time={timeline.now():.0f} ns")
    
    except KeyboardInterrupt:
        logger.info("🛑 Stopping quantum tunnel...")
        simulation_running = False

if __name__ == "__main__":
    main()