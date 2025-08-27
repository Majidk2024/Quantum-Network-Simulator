#!/usr/bin/env python3
"""
SeQUeNCe Quantum Tunnel Implementation with 250ms RTT
Transmits classical ORAN data through quantum network simulation
Uses SeQUeNCe discrete event simulation for precise timing
"""

import logging
import threading
import time
import select
from sctp import sctpsocket_tcp
from socket import AF_INET
import sys
import os

# Add SeQUeNCe to path
sys.path.append('/home/majid/Globcom2025_vmcpy/Globcom2025/sequence/SeQUeNCe')

# SeQUeNCe imports
from sequence.kernel.timeline import Timeline
from sequence.kernel.event import Event
from sequence.kernel.process import Process
from sequence.topology.node import Node

# Network Configuration
CU_IP = "10.108.202.32"
DU_IP = "10.108.202.33"
TUNNEL_IP = "10.109.202.32"
SCTP_PORT = 38472
BUFFER_SIZE = 128384

# Quantum delay configuration for 250ms RTT
# SeQUeNCe uses picoseconds: 1 second = 1e12 picoseconds
# 125ms = 0.125 seconds = 125 * 1e9 picoseconds
QUANTUM_DELAY_PS = int(125 * 1e9)  # 125ms in picoseconds
SIMULATION_TIME_PS = int(3600 * 1e12)  # 1 hour simulation

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sequence_quantum_tunnel.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('SeQUeNCe_Tunnel')

# Global variables
timeline = None
simulation_running = False
qcu_to_cu_socket = None
du_conn = None
pending_messages = {}
message_counter = 0

class QuantumTunnelNode(Node):
    """SeQUeNCe node that simulates quantum tunnel delay for classical data"""
    
    def __init__(self, name, timeline):
        super().__init__(name, timeline)
        self.name = name
        self.message_count = 0
        self.stats = {
            'messages_processed': 0,
            'total_bytes': 0,
            'start_time': time.time()
        }
        self.quantum_delay = QUANTUM_DELAY_PS
        
    def init(self):
        """Initialize the quantum tunnel node"""
        logger.info(f"🌌 Initializing {self.name} quantum tunnel node")
        
    def process_classical_data(self, data, destination, real_start_time):
        """Process classical data through quantum tunnel with delay"""
        self.message_count += 1
        self.pending_data = data
        self.real_start_time = real_start_time  # Store real start time
        self.data_start_time = self.timeline.now()  # Store simulation start time
        
        # Create unique event ID
        self.event_id = f"{self.name}_{self.message_count}"
        
        logger.info(f"🔬 [{self.name}] Processing classical data #{self.message_count}")
        logger.info(f"   📦 Data: {len(data)} bytes → {destination}")
        logger.info(f"   ⏰ Current: {self.timeline.now() / 1e12 * 1000:.3f}ms")
        
        # Schedule delivery after quantum delay
        delivery_time = self.timeline.now() + self.quantum_delay
        logger.info(f"   🎯 Delivery: {delivery_time / 1e12 * 1000:.3f}ms")
        logger.info(f"   ⌛ Delay: {self.quantum_delay / 1e12 * 1000:.0f}ms")
        logger.info(f"   📅 Event scheduled for {self.event_id}")
        
        # Create proper SeQUeNCe event with owner
        if destination == "CU":
            # Create a process that will handle the delivery
            process = Process(self, "deliver_to_cu", [])
            event = Event(delivery_time, process)
        else:
            # Create a process that will handle the delivery
            process = Process(self, "deliver_to_du", [])
            event = Event(delivery_time, process)
        
        self.timeline.schedule(event)

    def deliver_to_cu(self):
        """Deliver data to CU after quantum delay - SeQUeNCe process method"""
        try:
            if hasattr(self, 'pending_data') and self.pending_data:
                # 🔬 APPLY REAL-TIME DELAY HERE
                real_delay_start = time.time()
                
                # Calculate how much real time should have passed
                sim_delay_ms = (self.timeline.now() - self.data_start_time) / 1e12 * 1000
                expected_real_delay = sim_delay_ms / 1000.0  # Convert to seconds
                
                # Apply the actual real-time delay
                time.sleep(expected_real_delay)
                
                real_delay_actual = (time.time() - real_delay_start) * 1000
                
                logger.info(f"🎯 [QDU] Delivering {self.event_id}")
                logger.info(f"   📦 Data: {len(self.pending_data)} bytes → CU")
                logger.info(f"   🔬 Sim delay: {sim_delay_ms:.1f}ms")
                logger.info(f"   ⏰ Real delay: {real_delay_actual:.1f}ms")  # This should now be ~125ms
                
                # Send to CU
                if qcu_to_cu_socket:
                    qcu_to_cu_socket.send(self.pending_data)
                    logger.info(f"📡 [QDU] → CU: {len(self.pending_data)} bytes")
                    
                    total_delay = (time.time() - self.real_start_time) * 1000
                    logger.info(f"   🏁 Total delay: {total_delay:.1f}ms (✅)")
                    
                self.pending_data = None
                
        except Exception as e:
            logger.error(f"❌ Error delivering to CU: {e}")

    def deliver_to_du(self):
        """Deliver data to DU after quantum delay - SeQUeNCe process method"""
        try:
            if hasattr(self, 'pending_data') and self.pending_data:
                # 🔬 APPLY REAL-TIME DELAY HERE
                real_delay_start = time.time()
                
                # Calculate how much real time should have passed
                sim_delay_ms = (self.timeline.now() - self.data_start_time) / 1e12 * 1000
                expected_real_delay = sim_delay_ms / 1000.0  # Convert to seconds
                
                # Apply the actual real-time delay
                time.sleep(expected_real_delay)
                
                real_delay_actual = (time.time() - real_delay_start) * 1000
                
                logger.info(f"🎯 [QCU] Delivering {self.event_id}")
                logger.info(f"   📦 Data: {len(self.pending_data)} bytes → DU")
                logger.info(f"   🔬 Sim delay: {sim_delay_ms:.1f}ms")
                logger.info(f"   ⏰ Real delay: {real_delay_actual:.1f}ms")  # This should now be ~125ms
                
                # Send to DU
                if du_conn:
                    du_conn.send(self.pending_data)
                    logger.info(f"📡 [QCU] → DU: {len(self.pending_data)} bytes")
                    
                    total_delay = (time.time() - self.real_start_time) * 1000
                    logger.info(f"   🏁 Total delay: {total_delay:.1f}ms (✅)")
                    
                self.pending_data = None
                
        except Exception as e:
            logger.error(f"❌ Error delivering to DU: {e}")
    
    def log_statistics(self):
        """Log node statistics"""
        elapsed = time.time() - self.stats['start_time']
        rate = self.stats['messages_processed'] / elapsed if elapsed > 0 else 0
        
        logger.info(f"📊 [{self.name}] Statistics:")
        logger.info(f"   Messages: {self.stats['messages_processed']}")
        logger.info(f"   Bytes: {self.stats['total_bytes']}")
        logger.info(f"   Rate: {rate:.2f} msgs/sec")

def setup_sctp_connections():
    """Setup SCTP connections for CU and DU"""
    global qcu_to_cu_socket, du_conn
    
    logger.info("🔌 Setting up SCTP connections...")
    
    # QDU listens for DU connection
    logger.info(f"🔌 QDU listening at {TUNNEL_IP}:{SCTP_PORT}")
    qdu_to_du_socket = sctpsocket_tcp(AF_INET)
    qdu_to_du_socket.bind((TUNNEL_IP, SCTP_PORT))
    qdu_to_du_socket.listen(1)
    du_conn, du_addr = qdu_to_du_socket.accept()
    du_conn.setblocking(False)
    logger.info(f"✅ DU connected from {du_addr}")
    
    # QCU connects to CU
    qcu_to_cu_socket = sctpsocket_tcp(AF_INET)
    qcu_to_cu_socket.connect((DU_IP, SCTP_PORT))
    qcu_to_cu_socket.setblocking(False)
    logger.info(f"✅ QCU connected to CU at {DU_IP}:{SCTP_PORT}")
    
    logger.info("✅ SCTP connections established")

def handle_sctp_data(qcu_node, qdu_node):
    """Handle SCTP data with quantum tunnel delays"""
    logger.info("🚀 Starting SCTP handler with quantum tunnel...")
    
    while simulation_running:
        try:
            sockets_to_check = []
            if qcu_to_cu_socket:
                sockets_to_check.append(qcu_to_cu_socket)
            if du_conn:
                sockets_to_check.append(du_conn)
            
            if not sockets_to_check:
                time.sleep(0.1)
                continue
            
            readable, _, _ = select.select(sockets_to_check, [], [], 0.01)  # Shorter timeout
            
            # Handle CU to DU (via QCU quantum processing)
            if qcu_to_cu_socket in readable:
                try:
                    data = qcu_to_cu_socket.recv(BUFFER_SIZE)
                    if data:
                        real_start_time = time.time()
                        logger.info(f"📨 [CU → QCU] Received {len(data)} bytes")
                        
                        # Process through QCU with quantum delay
                        qcu_node.process_classical_data(data, "DU", real_start_time)
                        
                except Exception as e:
                    logger.error(f"❌ Error handling CU data: {e}")
            
            # Handle DU to CU (via QDU quantum processing)
            if du_conn in readable:
                try:
                    data = du_conn.recv(BUFFER_SIZE)
                    if data:
                        real_start_time = time.time()
                        logger.info(f"📨 [DU → QDU] Received {len(data)} bytes")
                        
                        # Process through QDU with quantum delay
                        qdu_node.process_classical_data(data, "CU", real_start_time)
                        
                except Exception as e:
                    logger.error(f"❌ Error handling DU data: {e}")
            
            # CRITICAL: Always run timeline to process scheduled events
            if timeline.events:
                timeline.run()
                        
        except Exception as e:
            logger.error(f"❌ SCTP handler error: {e}")
            time.sleep(0.1)

def statistics_thread(qcu_node, qdu_node):
    """Log statistics periodically"""
    while simulation_running:
        time.sleep(30)  # Log every 30 seconds
        if simulation_running:
            qcu_node.log_statistics()
            qdu_node.log_statistics()

def run_sequence_simulation():
    """Run SeQUeNCe simulation engine continuously"""
    global timeline, simulation_running
    
    logger.info("🌌 Starting SeQUeNCe simulation engine...")
    
    try:
        while simulation_running:
            # CRITICAL: Continuously process timeline events
            if timeline and timeline.events:
                timeline.run()
            
            # Very small delay to prevent busy waiting
            time.sleep(0.0001)  # 0.1ms delay
            
    except Exception as e:
        logger.error(f"❌ SeQUeNCe simulation error: {e}")
    
    logger.info("🌌 SeQUeNCe simulation engine stopped")

def main():
    """Main function to run SeQUeNCe quantum tunnel"""
    global timeline, simulation_running
    
    logger.info("🌌 Starting SeQUeNCe Quantum Tunnel for ORAN")
    logger.info("   Architecture: CU ↔ QCU ↔ [Quantum Tunnel] ↔ QDU ↔ DU")
    logger.info(f"   Quantum Delay: {QUANTUM_DELAY_PS/1e9:.0f}ms each direction")
    logger.info(f"   Expected RTT: {2*QUANTUM_DELAY_PS/1e9:.0f}ms")
    
    try:
        # Initialize SeQUeNCe timeline
        timeline = Timeline(SIMULATION_TIME_PS)
        timeline.init()  # Initialize timeline
        
        # Create quantum nodes
        qcu_node = QuantumTunnelNode("QCU", timeline)
        qdu_node = QuantumTunnelNode("QDU", timeline)
        
        # Initialize nodes
        qcu_node.init()
        qdu_node.init()
        
        logger.info("✅ SeQUeNCe quantum nodes created")
        logger.info(f"🌌 Quantum tunnel established: QCU ↔ QDU")
        logger.info(f"⏱️  Each direction delay: {QUANTUM_DELAY_PS/1e9:.0f}ms")
        logger.info(f"🔄 Round-trip time (RTT): {2*QUANTUM_DELAY_PS/1e9:.0f}ms")
        
        # Setup SCTP connections
        setup_sctp_connections()
        
        # Start simulation
        simulation_running = True
        logger.info("🚀 Starting quantum tunnel bridge...")
        
        # Start SCTP data handler thread
        sctp_thread = threading.Thread(target=handle_sctp_data, args=(qcu_node, qdu_node), daemon=True)
        sctp_thread.start()
        
        # Start SeQUeNCe simulation thread
        sim_thread = threading.Thread(target=run_sequence_simulation, daemon=True)
        sim_thread.start()
        
        # Start statistics logging thread
        stats_thread = threading.Thread(target=statistics_thread, args=(qcu_node, qdu_node), daemon=True)
        stats_thread.start()
        
        logger.info("✅ All threads started - Quantum tunnel is ACTIVE")
        logger.info("📡 Ready to relay CU ↔ QCU ↔ QDU ↔ DU traffic")
        logger.info(f"🎯 Expected RTT through quantum tunnel: {2*QUANTUM_DELAY_PS/1e9:.0f}ms")
        logger.info("Press Ctrl+C to stop")
        
        # Keep main thread alive
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Stopping quantum tunnel...")
        
    except Exception as e:
        logger.error(f"❌ Main error: {e}")
        
    finally:
        simulation_running = False
        logger.info("🌌 SeQUeNCe quantum tunnel stopped")

if __name__ == "__main__":
    main()
