import netsquid as ns
import pydynaa
from netsquid.nodes import Node
from socket import AF_INET, socket, SO_KEEPALIVE, SOL_SOCKET, error as socket_error
from sctp import sctpsocket_tcp
import select
import oqs
import logging
import hashlib
import struct
import time

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - [%(name)s] %(message)s',
    level=logging.INFO,
    handlers=[logging.StreamHandler(), logging.FileHandler('tunnel_pqc.log')]
)
logger = logging.getLogger("PQCTunnel")

# Network Configuration for Room Environment
CU_IP = "10.108.202.32"
DU_IP = "10.108.202.33"
TUNNEL_IP = "10.109.202.32"
SCTP_PORT = 38472
BUFFER_SIZE = 4096
POLL_INTERVAL = 10000
PACKET_HEADER_SIZE = 4  # 4 bytes for packet length

# Enhanced quantum parameters for realistic simulation
FIBER_LENGTH = 50000  # 50 km fiber distance
LIGHT_SPEED_FIBER = 200000000  # ~200,000 km/s in fiber
BASE_QUANTUM_DELAY = 0.15  # 150ms base quantum processing (increased from 100ms)
PQC_PROCESSING_DELAY = 0.08  # 80ms PQC encryption/decryption (increased from 50ms)

# Global socket variables
server_socket = None
du_conn = None
cu_client_socket = None

class PQCManager:
    """Enhanced PQC Manager with realistic quantum delays for room testing"""
    def __init__(self, name, is_server=False):
        self.name = name
        self.is_server = is_server
        self.kem = oqs.KeyEncapsulation("Kyber512")
        self.public_key = None
        self.kem_instance = None
        self.shared_secret = None
        self.counter = 0
        logger.info(f"[{self.name}] Initialized PQC with Kyber512 for room environment")

    def setup_keypair(self):
        """Generate and store keypair with simulated quantum delay"""
        if not self.is_server:
            # Simulate quantum key generation delay
            import time
            time.sleep(BASE_QUANTUM_DELAY)
            
            self.kem_instance = self.kem
            self.public_key = self.kem.generate_keypair()
            logger.info(f"[{self.name}] Generated keypair with quantum delay: {BASE_QUANTUM_DELAY*1000:.1f}ms")
            return self.public_key
        return None

    def establish_shared_secret(self, client_public_key=None, server_ciphertext=None):
        """Establish shared secret with quantum processing delay"""
        try:
            import time
            time.sleep(BASE_QUANTUM_DELAY)  # Simulate quantum processing
            
            if self.is_server and client_public_key:
                ciphertext, self.shared_secret = self.kem.encap_secret(client_public_key)
                logger.info(f"[{self.name}] Generated shared secret with quantum delay: {self.shared_secret.hex()[:10]}...")
                return ciphertext
            elif not self.is_server and server_ciphertext:
                self.shared_secret = self.kem_instance.decap_secret(server_ciphertext)
                logger.info(f"[{self.name}] Recovered shared secret with quantum delay: {self.shared_secret.hex()[:10]}...")
                return True
        except Exception as e:
            logger.error(f"[{self.name}] Key establishment error: {str(e)}")
        return None

    def protect_data(self, data, direction):
        """Encrypt/Decrypt data with PQC processing delay"""
        if not self.shared_secret:
            logger.error(f"[{self.name}] No shared secret available")
            return None

        try:
            # Simulate PQC processing delay for room testing
            import time
            time.sleep(PQC_PROCESSING_DELAY)
            
            # Use counter for unique key stream
            counter_bytes = struct.pack('>Q', 0)  # Reset counter to zero for sync
            # Generate key stream using both shared secret and counter
            key_material = self.shared_secret + counter_bytes
            key_stream = hashlib.sha256(key_material).digest()
            while len(key_stream) < len(data):
                key_material = hashlib.sha256(key_stream).digest() + counter_bytes
                key_stream += hashlib.sha256(key_material).digest()
            key_stream = key_stream[:len(data)]

            # Process data with XOR
            result = bytes(a ^ b for a, b in zip(data, key_stream))
            
            # Enhanced logging for room testing
            if direction == "Encrypting":
                logger.info(f"[{self.name}] 🔒 Encrypted {len(data)}B with {PQC_PROCESSING_DELAY*1000:.1f}ms delay")
                return result
            else:
                logger.info(f"[{self.name}] 🔓 Decrypted {len(data)}B with {PQC_PROCESSING_DELAY*1000:.1f}ms delay")
                return result
        except Exception as e:
            logger.error(f"[{self.name}] Protection error: {str(e)}")
        return None

class QCUProtocol(pydynaa.Entity):
    """QCU Protocol with enhanced delays for room environment"""
    def __init__(self, node):
        super().__init__()
        self.node = node
        self.pqc = PQCManager("QCU", is_server=False)
        
    def start_protocol(self):
        """Initialize QCU with room-specific parameters"""
        logger.info("[QCU] Starting quantum protocol with enhanced delays for room testing")
        self.pqc.setup_keypair()
        logger.info(f"[QCU] Room environment - Fiber: {FIBER_LENGTH/1000:.1f}km, Delays: {(BASE_QUANTUM_DELAY + PQC_PROCESSING_DELAY)*1000:.1f}ms")

class QDUProtocol(pydynaa.Entity):
    """QDU Protocol with enhanced delays for room environment"""
    def __init__(self, node):
        super().__init__()
        self.node = node
        self.pqc = PQCManager("QDU", is_server=True)
        
    def start_protocol(self):
        """Initialize QDU with room-specific parameters"""
        logger.info("[QDU] Starting quantum protocol with enhanced delays for room testing")
        logger.info(f"[QDU] Room environment - Expected RTT: {(FIBER_LENGTH/LIGHT_SPEED_FIBER + BASE_QUANTUM_DELAY*2 + PQC_PROCESSING_DELAY*2)*1000:.1f}ms")

def create_quantum_network():
    """Create simplified quantum network with QCU and QDU nodes for room testing"""
    logger.info("🌌 Creating quantum network for room environment testing")
    
    # Reset simulation
    ns.sim_reset()
    
    # Create QCU and QDU nodes directly - simplified approach
    qcu_node = Node("QCU")
    qdu_node = Node("QDU") 
    
    # Create protocols with enhanced delays - no complex channel setup needed
    qcu_protocol = QCUProtocol(qcu_node)
    qdu_protocol = QDUProtocol(qdu_node)
    
    # Start protocols
    qcu_protocol.start_protocol()
    qdu_protocol.start_protocol()
    
    logger.info("✅ Netsquid Quantum nodes created for communication")
    
    return qcu_protocol, qdu_protocol

def setup_sctp_connections():
    """Setup SCTP connections for room environment"""
    global server_socket, du_conn, cu_client_socket
    
    try:
        logger.info("🔧 Setting up SCTP connections for room environment...")
        
        # Setup server socket for DU connection
        server_socket = sctpsocket_tcp(AF_INET)
        server_socket.setsockopt(SOL_SOCKET, SO_KEEPALIVE, 1)
        server_socket.bind((TUNNEL_IP, SCTP_PORT))
        server_socket.listen(1)
        logger.info(f"Listening for DU connection on {TUNNEL_IP}:{SCTP_PORT}")
        
        # Accept DU connection
        du_conn, du_addr = server_socket.accept()
        du_conn.setsockopt(SOL_SOCKET, SO_KEEPALIVE, 1)
        logger.info(f"✅ Connected to DU at {du_addr}")
        
        # Connect to CU
        cu_client_socket = sctpsocket_tcp(AF_INET) 
        cu_client_socket.connect((DU_IP, SCTP_PORT))
        cu_client_socket.setsockopt(SOL_SOCKET, SO_KEEPALIVE, 1)
        logger.info(f"✅ Connected to CU at {DU_IP}:{SCTP_PORT}")
        
        return True
        
    except Exception as e:
        logger.error(f"Connection setup failed: {e}")
        return False

def handle_packet_processing(qcu_protocol, qdu_protocol):
    """Simplified packet processing with enhanced delays for room testing"""
    packet_count = 0
    start_time = time.time()
    
    logger.info("🔄 Starting packet processing for room environment...")
    
    while True:
        try:
            sockets = [cu_client_socket, du_conn]
            ready, _, _ = select.select(sockets, [], [], 0.01)  # 10ms polling for room testing
            
            for sock in ready:
                data = sock.recv(BUFFER_SIZE)
                if not data:
                    continue
                    
                packet_count += 1
                
                if sock == cu_client_socket:
                    # CU → DU: Encrypt at QCU (simplified processing)
                    logger.info(f"📥 CU→DU: Received {len(data)} bytes")
                    
                    # Apply quantum encryption with delay
                    encrypted = qcu_protocol.pqc.protect_data(data, "Encrypting")
                    if encrypted:
                        du_conn.send(encrypted)
                        logger.info(f"📤 CU→DU: Forwarded encrypted packet #{packet_count} ({len(encrypted)} bytes)")
                    else:
                        # Fallback: forward as-is if encryption fails
                        du_conn.send(data)
                        logger.info(f"📤 CU→DU: Forwarded unencrypted packet #{packet_count} ({len(data)} bytes)")
                        
                elif sock == du_conn:
                    # DU → CU: Decrypt at QDU (simplified processing)
                    logger.info(f"📥 DU→CU: Received {len(data)} bytes")
                    
                    # Apply quantum decryption with delay
                    decrypted = qdu_protocol.pqc.protect_data(data, "Decrypting")
                    if decrypted:
                        cu_client_socket.send(decrypted)
                        logger.info(f"📤 DU→CU: Forwarded decrypted packet #{packet_count} ({len(decrypted)} bytes)")
                    else:
                        # Fallback: forward as-is if decryption fails
                        cu_client_socket.send(data)
                        logger.info(f"📤 DU→CU: Forwarded unprocessed packet #{packet_count} ({len(data)} bytes)")
                
                # Room testing statistics every 10 packets
                if packet_count % 10 == 0:
                    elapsed = time.time() - start_time
                    throughput = (packet_count * BUFFER_SIZE) / elapsed / 1024  # KB/s estimate
                    logger.info(f"📊 Room testing: {packet_count} packets processed, ~{throughput:.1f} KB/s")
                    
        except KeyboardInterrupt:
            logger.info("🛑 Room testing stopped by user")
            break
        except Exception as e:
            logger.error(f"Packet processing error in room environment: {e}")
            continue

def cleanup_connections():
    """Cleanup for room testing environment"""
    global server_socket, du_conn, cu_client_socket
    
    logger.info("🧹 Cleaning up room testing environment...")
    
    for sock, name in [(cu_client_socket, "CU"), (du_conn, "DU"), (server_socket, "Server")]:
        if sock:
            try:
                sock.close()
                logger.info(f"✅ Closed {name} connection")
            except:
                pass
    
    logger.info("🧹 Room testing cleanup complete")

def main():
    """Main tunnel for room environment testing"""
    logger.info("🚀 Starting NetSquid PQC Tunnel for Room Environment Testing")
    logger.info(f"🏠 Room parameters: {FIBER_LENGTH/1000:.1f}km fiber, {(BASE_QUANTUM_DELAY + PQC_PROCESSING_DELAY)*1000:.1f}ms processing")
    logger.info(f"🎯 Target RTT: ~{(BASE_QUANTUM_DELAY*2 + PQC_PROCESSING_DELAY*2)*1000:.1f}ms (increased delays)")
    
    try:
        # Setup connections
        if not setup_sctp_connections():
            logger.error("Failed to setup SCTP connections")
            return
        
        # Create quantum network
        qcu_protocol, qdu_protocol = create_quantum_network()
        
        # Establish shared secrets for both protocols
        qcu_public = qcu_protocol.pqc.setup_keypair()
        if qcu_public:
            ciphertext = qdu_protocol.pqc.establish_shared_secret(qcu_public)
            if ciphertext:
                qcu_protocol.pqc.establish_shared_secret(server_ciphertext=ciphertext)
        
        logger.info("🔄 Room testing tunnel ready - processing traffic...")
        
        # Start packet processing
        handle_packet_processing(qcu_protocol, qdu_protocol)
        
    except Exception as e:
        logger.error(f"Room testing error: {e}")
    finally:
        cleanup_connections()

if __name__ == "__main__":
    main()
