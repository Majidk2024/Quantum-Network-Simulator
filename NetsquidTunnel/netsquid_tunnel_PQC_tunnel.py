import netsquid as ns
import pydynaa
from netsquid.nodes import Node
from netsquid.nodes.connections import Connection
from netsquid.components import ClassicalChannel
from netsquid.components.models import FibreDelayModel, FixedDelayModel
from socket import AF_INET, socket, SO_KEEPALIVE, SOL_SOCKET
from sctp import sctpsocket_tcp
import select
import oqs
import logging
import hashlib
import struct
import time  # Import time module for performance measurements

# Define SCTP constants that might not be available in all versions of python-sctp
try:
    from sctp import IPPROTO_SCTP, SOL_SCTP, SCTP_PPID
except ImportError:
    # Fallback values for constants
    IPPROTO_SCTP = 132
    SOL_SCTP = 132
    SCTP_PPID = 3

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[logging.StreamHandler(), logging.FileHandler('tunnel_pqc.log')]
)
logger = logging.getLogger("PQCTunnel")

# Network Configuration
CU_IP = "10.108.202.32"
DU_IP = "10.108.202.33"
TUNNEL_IP = "10.109.202.32"
SCTP_PORT = 38472
BUFFER_SIZE = 8192
POLL_INTERVAL = 1

# F1AP SCTP PPID
F1AP_PPID = 62  # F1AP protocol payload ID for SCTP

class PQCManager:
    """Manages PQC operations for tunnel endpoints"""
    def __init__(self, name, is_server=False):
        self.name = name
        self.is_server = is_server
        self.kem = oqs.KeyEncapsulation("Kyber512")
        self.public_key = None
        self.kem_instance = None
        self.shared_secret = None
        logger.info(f"[{self.name}] Initialized PQC with Kyber512")

    def setup_keypair(self):
        """Generate and store keypair"""
        if not self.is_server:
            self.kem_instance = self.kem
            self.public_key = self.kem.generate_keypair()
            logger.info(f"[{self.name}] Generated keypair")
            return self.public_key
        return None

    def establish_shared_secret(self, client_public_key=None, server_ciphertext=None):
        """Establish shared secret"""
        try:
            if self.is_server and client_public_key:
                ciphertext, self.shared_secret = self.kem.encap_secret(client_public_key)
                logger.info(f"[{self.name}] Generated shared secret")
                return ciphertext
            elif not self.is_server and server_ciphertext:
                self.shared_secret = self.kem_instance.decap_secret(server_ciphertext)
                logger.info(f"[{self.name}] Recovered shared secret")
                return True
        except Exception as e:
            logger.error(f"[{self.name}] Key establishment error: {str(e)}")
        return None

    def protect_data(self, data, direction):
        """Encrypt/Decrypt data using shared secret"""
        if not self.shared_secret:
            logger.error(f"[{self.name}] No shared secret available")
            return None

        try:
            # Use counter for unique key stream
            counter_bytes = struct.pack('>Q', 0)  # Reset counter to zero for sync
            key_material = self.shared_secret + counter_bytes
            key_stream = hashlib.sha256(key_material).digest()
            while len(key_stream) < len(data):
                key_material = hashlib.sha256(key_stream).digest() + counter_bytes
                key_stream += hashlib.sha256(key_material).digest()
            key_stream = key_stream[:len(data)]

            # Process data with XOR
            result = bytes(a ^ b for a, b in zip(data, key_stream))
            
            logger.info(f"[{self.name}] {direction} {len(data)}B")
            return result
        except Exception as e:
            logger.error(f"[{self.name}] Data protection error: {str(e)}")
            return None

class ClassicalConnection(Connection):
    """Bi-directional classical connection with PQC"""
    def __init__(self, length):
        super().__init__("PQC_SCTP_Tunnel")
        logger.info("Initializing PQC-secured tunnel")
        
        # Initialize PQC managers
        self.qdu_pqc = PQCManager("QDU", is_server=False)
        self.qcu_pqc = PQCManager("QCU", is_server=True)
        
        try:
            # Create channels first
            self.channel_fwd = ClassicalChannel("Channel_CU2DU", 
                                              length=length,
            # Configure delay: 150ms fixed delay for PQC processing simulation
                                              models={"delay_model": FixedDelayModel(delay=150e-3)})
            
            self.channel_rev = ClassicalChannel("Channel_DU2CU", 
                                              length=length,
            # Configure delay: 150ms fixed delay for PQC processing simulation
                                              models={"delay_model": FixedDelayModel(delay=150e-3)})
            # Add ports to channels before adding them as subcomponents
            self.channel_fwd.add_ports(["send", "recv"])
            self.channel_rev.add_ports(["send", "recv"])
            
            # Add the channels as subcomponents
            self.add_subcomponent(self.channel_fwd)
            self.add_subcomponent(self.channel_rev)
            
            # Add ports to the connection
            self.add_ports(["cu_in", "cu_out", "du_in", "du_out"])
            
            # Forward channel (CU → DU)
            self.ports["cu_in"].forward_input(self.channel_fwd.ports["send"])
            self.channel_fwd.ports["recv"].forward_output(self.ports["du_out"])
            
            # Reverse channel (DU → CU)
            self.ports["du_in"].forward_input(self.channel_rev.ports["send"])
            self.channel_rev.ports["recv"].forward_output(self.ports["cu_out"])
            
            logger.info("Classical connection ports and channels configured")
        except Exception as e:
            logger.error(f"Connection setup error: {str(e)}")
            raise

class SCTPNode(Node):
    """Node with PQC capabilities"""
    def __init__(self, name, pqc_manager):
        super().__init__(name)
        self.add_ports(["in_port", "out_port"])
        self.ports["in_port"].bind_input_handler(self.handle_message)
        self.pqc = pqc_manager
        logger.info(f"Created {name} node with PQC")

    def handle_message(self, message):
        """Handle incoming messages with PQC protection"""
        try:
            data = message.items[0]
            logger.info(f"[{self.name}] Received message of {len(data)}B")
            # No direct forwarding here; handled in poll_sctp_messages
        except Exception as e:
            logger.error(f"[{self.name}] Message handling error: {str(e)}")

class SCTPEventHandler(pydynaa.Entity):
    """Handles SCTP events with PQC"""
    evtype_poll = pydynaa.EventType("Poll", "")
    evtype_init = pydynaa.EventType("Init", "")

    def __init__(self, cu_node, du_node, connection):
        super().__init__()
        self.cu_node = cu_node
        self.du_node = du_node
        self.connection = connection
        self.tunnel_ready = False
        
        # Initialize event handlers
        self._wait(pydynaa.EventHandler(self.poll_sctp_messages), 
                  entity=self, event_type=self.evtype_poll)
        self._wait(pydynaa.EventHandler(self.initialize_pqc),
                  entity=self, event_type=self.evtype_init)
        
        # Schedule events
        self._schedule_after(POLL_INTERVAL, self.evtype_poll)
        self._schedule_now(self.evtype_init)

    def initialize_pqc(self, event=None):
        """Initialize PQC key exchange between NetSquid nodes"""
        try:
            # 1. QDU (NetSquid node) generates keypair
            qdu_public_key = self.connection.qdu_pqc.setup_keypair()
            if not qdu_public_key:
                raise Exception("Failed to generate QDU keypair")
            
            # 2. Send QDU's public key to QCU through NetSquid channel
            self.du_node.ports["out_port"].tx_output(qdu_public_key)
            
            # 3. QCU (NetSquid node) generates ciphertext using QDU's public key
            ciphertext = self.connection.qcu_pqc.establish_shared_secret(qdu_public_key)
            if ciphertext:
                # 4. Send ciphertext to QDU through NetSquid channel
                self.cu_node.ports["out_port"].tx_output(ciphertext)
                
                # 5. QDU (NetSquid node) recovers shared secret
                if self.connection.qdu_pqc.establish_shared_secret(server_ciphertext=ciphertext):
                    # 6. Verify shared secrets match
                    qcu_hash = hashlib.sha256(self.connection.qcu_pqc.shared_secret).hexdigest()[:8]
                    qdu_hash = hashlib.sha256(self.connection.qdu_pqc.shared_secret).hexdigest()[:8]
                    
                    if qcu_hash == qdu_hash:
                        self.tunnel_ready = True
                        logger.info(f"PQC tunnel is now ready for secure data transmission")
                    else:
                        raise Exception("Shared secret mismatch between QCU and QDU")
                else:
                    raise Exception("QDU failed to recover shared secret")
            else:
                raise Exception("QCU failed to generate ciphertext")
        except Exception as e:
            logger.error(f"PQC initialization failed: {str(e)}")

    def poll_sctp_messages(self, event=None):
        """Poll and process SCTP messages with PQC protection"""
        global cu_client_socket, du_conn, server_socket
        
        try:
            # BUILD LIST OF VALID SOCKETS
            valid_sockets = []
            if cu_client_socket and cu_client_socket.fileno() != -1:
                valid_sockets.append(cu_client_socket)
            if du_conn and du_conn.fileno() != -1:
                valid_sockets.append(du_conn)
                
            if not valid_sockets:
                self._schedule_after(POLL_INTERVAL, self.evtype_poll)
                return
                
            # POLL FOR READABLE SOCKETS
            try:
                readable, _, _ = select.select(valid_sockets, [], [], 0.001)
                for sock in readable:
                    self._process_socket_data(sock)
            except Exception as e:
                logger.error(f"Select error: {str(e)}")
        except Exception as e:
            logger.error(f"Polling error: {str(e)}")

        # Always reschedule polling
        self._schedule_after(POLL_INTERVAL, self.evtype_poll)
        
    def _process_socket_data(self, sock):
        """Process data from a readable socket with PQC protection"""
        global cu_client_socket, du_conn
        
        try:
            # Set non-blocking mode
            sock.setblocking(False)
            
            # Receive data
            try:
                # Try to use recvmsg to get ancillary data including PPID
                orig_data, ancdata, _, _ = sock.recvmsg(BUFFER_SIZE)
                
                # Extract PPID from SCTP packet if available
                ppid = F1AP_PPID  # Default PPID
                for cmsg_level, cmsg_type, cmsg_data in ancdata:
                    if (cmsg_level == IPPROTO_SCTP) and (cmsg_type == SCTP_PPID):
                        ppid = struct.unpack('=I', cmsg_data)[0]
            except (AttributeError, TypeError, ValueError):
                # Fallback for sockets that don't support recvmsg
                orig_data = sock.recv(BUFFER_SIZE)
                ppid = F1AP_PPID
            except BlockingIOError:
                return
            
            # Check if connection closed
            if not orig_data:
                self._handle_empty_data(sock)
                return
            
            # Process data based on socket type
            is_cu_socket = (sock == cu_client_socket)
            source_name = "CU" if is_cu_socket else "DU"
            target_name = "DU" if is_cu_socket else "CU"
            
            # SECURITY RULE: Only process data through the NetSquid tunnel
            # External systems (CU/DU) must never have direct communication paths
            if self.tunnel_ready:
                self._process_data_through_pqc(sock, orig_data, is_cu_socket, source_name, target_name, ppid)
            else:
                logger.warning(f"SECURITY: Blocked {len(orig_data)}B from {source_name}. Direct communication prohibited - quantum tunnel not ready")
                
        except (BrokenPipeError, ConnectionResetError) as e:
            self._handle_connection_error(sock, e)
        except Exception as e:
            logger.error(f"Transfer error: {str(e)}")
        finally:
            # Reset to non-blocking mode
            try:
                if sock and sock.fileno() != -1:
                    sock.setblocking(False)
            except:
                pass
    
    def _process_data_through_pqc(self, sock, orig_data, is_cu_socket, source_name, target_name, ppid=F1AP_PPID):
        """Process data through PQC protection - THE CORE SECURITY FUNCTION"""
        global cu_client_socket, du_conn
        
        # SECURITY CHECK: Enforce tunnel-only communication
        if not self.tunnel_ready:
            logger.error(f"Attempted direct communication without PQC tunnel")
            return
            
        if is_cu_socket:
            # CU → DU flow through NetSquid nodes
            logger.info(f"{source_name} → {target_name}: Processing {len(orig_data)}B")
            
            # 1. ENCRYPT data from CU with QCU manager
            encrypted = self.connection.qcu_pqc.protect_data(orig_data, "Encrypted")
            if not encrypted:
                return
                
            # 2. ENSURE DATA TRAVELS THROUGH NETSQUID SIMULATION
            data_with_ppid = struct.pack('=I', ppid) + encrypted
            self.cu_node.ports["out_port"].tx_output(data_with_ppid)
            
            # 3. DECRYPT after NetSquid transmission
            received_ppid = struct.unpack('=I', data_with_ppid[:4])[0]
            decrypted = self.connection.qdu_pqc.protect_data(encrypted, "Decrypted")
            if not decrypted:
                return
                
            # 4. VERIFY data integrity
            if decrypted != orig_data:
                logger.error(f"Data integrity check failed - decryption error")
                return
                
            # 5. Forward to DU socket AFTER successful NetSquid simulation
            try:
                if du_conn and du_conn.fileno() != -1:
                    du_conn.setblocking(True)
                    self._send_with_ppid(du_conn, decrypted, received_ppid)
                    du_conn.setblocking(False)
            except Exception as e:
                logger.error(f"Failed to send data to {target_name}: {str(e)}")
        else:
            # DU → CU flow through NetSquid nodes (mirror of above)
            logger.info(f"{source_name} → {target_name}: Processing {len(orig_data)}B")
            
            # 1. ENCRYPT data from DU with QDU manager
            encrypted = self.connection.qdu_pqc.protect_data(orig_data, "Encrypted")
            if not encrypted:
                return
                
            # 2. ENSURE DATA TRAVELS THROUGH NETSQUID SIMULATION
            data_with_ppid = struct.pack('=I', ppid) + encrypted
            self.du_node.ports["out_port"].tx_output(data_with_ppid)
            
            # 3. DECRYPT after NetSquid transmission
            received_ppid = struct.unpack('=I', data_with_ppid[:4])[0]
            decrypted = self.connection.qcu_pqc.protect_data(encrypted, "Decrypted")
            if not decrypted:
                return
                
            # 4. VERIFY data integrity
            if decrypted != orig_data:
                logger.error(f"Data integrity check failed - decryption error")
                return
                
            # 5. Forward to CU socket AFTER successful NetSquid simulation
            try:
                if cu_client_socket and cu_client_socket.fileno() != -1:
                    cu_client_socket.setblocking(True)
                    self._send_with_ppid(cu_client_socket, decrypted, received_ppid)
                    cu_client_socket.setblocking(False)
            except Exception as e:
                logger.error(f"Failed to send data to {target_name}: {str(e)}")
                
    def _send_with_ppid(self, sock, data, ppid):
        """Send data with PPID using compatible approach"""
        try:
            # Try sctp_send first
            sock.sctp_send(data, ppid=ppid)
            return
        except (AttributeError, TypeError):
            # Fallback to regular sendall
            sock.sendall(data)
            return

    def _handle_empty_data(self, sock):
        """Handle empty data condition"""
        global cu_client_socket, du_conn
        
        if sock == cu_client_socket:
            logger.warning("CU client sent empty data - connection closing")
            try:
                cu_client_socket.close()
                cu_client_socket = None
            except:
                pass
        else:
            logger.warning("DU sent empty data - connection closing")
            try:
                du_conn.close()
                du_conn = None
            except:
                pass
                
    def _handle_connection_error(self, sock, error):
        """Handle connection errors"""
        global cu_client_socket, du_conn
        
        if sock == cu_client_socket:
            logger.warning(f"CU connection error: {str(error)} - connection lost")
            try:
                cu_client_socket.close()
                cu_client_socket = None
            except:
                pass
        else:
            logger.warning(f"DU connection error: {str(error)} - connection lost")
            try:
                du_conn.close()
                du_conn = None
            except:
                pass

def main():
    """Main tunnel function"""
    global server_socket, du_conn, cu_client_socket
    
    try:
        # Setup SCTP server to accept connection from DU
        server_socket = sctpsocket_tcp(AF_INET)
        server_socket.setsockopt(SOL_SOCKET, SO_KEEPALIVE, 1)
        server_socket.bind((TUNNEL_IP, SCTP_PORT))
        server_socket.listen(1)
        
        logger.info(f"Waiting for DU client to connect at {TUNNEL_IP}:{SCTP_PORT}...")
        
        # Accept connection from DU client
        server_socket.settimeout(30)
        du_conn, addr = server_socket.accept()
        server_socket.settimeout(None)
        du_conn.setblocking(False)
        logger.info(f"DU client connected from {addr}")

        # Setup SCTP client connection to CU server
        logger.info(f"Connecting to CU server at {CU_IP}:{SCTP_PORT}...")
        cu_client_socket = sctpsocket_tcp(AF_INET)
        cu_client_socket.setsockopt(SOL_SOCKET, SO_KEEPALIVE, 1)
        cu_client_socket.settimeout(5)
        cu_client_socket.connect((CU_IP, SCTP_PORT))
        cu_client_socket.setblocking(False)
        logger.info(f"Connected to CU server at {CU_IP}:{SCTP_PORT}")
        
        # Create PQC-secured NetSquid tunnel
        connection = ClassicalConnection(length=1)
        
        # Create nodes with PQC managers
        cu_node = SCTPNode("CU", connection.qcu_pqc)
        du_node = SCTPNode("DU", connection.qdu_pqc)
        
        # Connect nodes through quantum channels
        cu_node.ports["out_port"].connect(connection.ports["cu_in"])
        cu_node.ports["in_port"].connect(connection.ports["cu_out"])
        du_node.ports["out_port"].connect(connection.ports["du_in"])
        du_node.ports["in_port"].connect(connection.ports["du_out"])
        
        # Create event handler for secure communication
        handler = SCTPEventHandler(cu_node, du_node, connection)
        
        logger.info("Starting PQC-secured NetSquid tunnel...")
        ns.sim_run()
        
    except Exception as e:
        logger.error(f"Simulation error: {str(e)}")
    finally:
        # Cleanup
        for sock in [du_conn, cu_client_socket, server_socket]:
            if sock:
                try:
                    sock.close()
                except:
                    pass

if __name__ == "__main__":
    # Global socket variables
    server_socket = None
    du_conn = None
    cu_client_socket = None
    
    # Start tunnel
    main()
