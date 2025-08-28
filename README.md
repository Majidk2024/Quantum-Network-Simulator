# Quantum-Ready OAI CN5G

This repository extends the [OAI CN5G](https://gitlab.eurecom.fr/oai/cn5g/oai-cn5g-fed) core network setup with **quantum-ready tunnels**.  
It integrates **classical SCTP tunneling** with **quantum network simulators (QuNetSim, SimQN, NetSquid)** for experimental research on **post-quantum and quantum-assisted 5G architectures**.

---

## 🚀 Features
- Standard **OAI CN5G Core** with Docker (AMF, SMF, UPF, DN, MySQL).
- **Classical SCTP tunnel** for CU–DU communication.
- **Quantum tunnels** using:
  - [QuNetSim](https://github.com/tqsd/QuNetSim) (threaded & async modes)
  - [SimQN](https://github.com/ScQ-Cloud/SimQN)
  - [NetSquid](https://netsquid.org/)
- Support for **sequence tunneling** & delay/jitter evaluation.
- Ready for integration with **UE, DU, and CU nodes**.

---

## 📦 Prerequisites
- **OS**: Ubuntu 20.04 / 22.04  
- **Dependencies**:
  ```bash
  sudo apt update
  sudo apt install -y git docker docker-compose python3 python3-pip
