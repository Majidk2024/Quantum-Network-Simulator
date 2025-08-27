from qns.simulator.simulator import Simulator
from qns.simulator.event import Event
from qns.entity.node.app import Application
from qns.entity.node.node import QNode
from qns.entity.cchannel.cchannel import ClassicChannel, ClassicPacket, RecvClassicPacket
from qns.simulator import func_to_event


class DummyDUApp(Application):
    def __init__(self, dest: QNode, channel: ClassicChannel):
        super().__init__()
        self.dest = dest
        self.channel = channel
        self.add_handler(self.handle_recv_packet, [RecvClassicPacket], [])

    def install(self, node: QNode, simulator: Simulator):
        super().install(node, simulator)
        self.send_dummy_data()

    def send_dummy_data(self):
        # Simulate sending a message to CU
        data = b"Hello from DU"
        packet = ClassicPacket(msg=data, src=self.get_node(), dest=self.dest)
        self.channel.send(packet=packet, next_hop=self.dest)

    def handle_recv_packet(self, node: QNode, event: Event):
        data = event.packet.get()
        print(f"📥 [DU] received: {data.decode()}")


class DummyCUApp(Application):
    def __init__(self, dest: QNode, channel: ClassicChannel):
        super().__init__()
        self.dest = dest
        self.channel = channel
        self.add_handler(self.handle_recv_packet, [RecvClassicPacket], [])

    def install(self, node: QNode, simulator: Simulator):
        super().install(node, simulator)

    def handle_recv_packet(self, node: QNode, event: Event):
        data = event.packet.get()
        print(f"📥 [CU] received: {data.decode()}")

        # Respond to DU
        response = b"Hello from CU"
        packet = ClassicPacket(msg=response, src=self.get_node(), dest=self.dest)
        self.channel.send(packet=packet, next_hop=self.dest)


# Create nodes and channel
qdu_node = QNode("QDU")
qcu_node = QNode("QCU")
channel = ClassicChannel(name="simqn_tunnel")

qdu_node.add_cchannel(channel)
qcu_node.add_cchannel(channel)

# Add dummy traffic apps
du_app = DummyDUApp(dest=qcu_node, channel=channel)
cu_app = DummyCUApp(dest=qdu_node, channel=channel)

qdu_node.add_apps(du_app)
qcu_node.add_apps(cu_app)

# Setup simulator
sim = Simulator(start_time=0, end_time=10, accuracy=1000)
qdu_node.install(sim)
qcu_node.install(sim)

# Run simulation
sim.run()


