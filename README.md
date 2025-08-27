# Quantum-Ready OAI 5G Deployment with PQC Integration

## 📌 Abstract
The rise of quantum computing poses a major threat to traditional ciphers, specifically making the Radio Access Network (RAN) vulnerable to future quantum-based attacks.  

To address this challenge, this project proposes **Quantum-Inspired RAN (Q-RAN)** — a next-generation framework designed to future-proof telecom networks against quantum threats.  

As a foundation, we integrate **quantum network simulators** with the **OpenAirInterface (OAI) 5G stack** to deploy a standalone 5G network capable of supporting quantum operations. The integration introduces **Quantum Gateways (Qtunnels)** that secure the F1 interface between the Central Unit (CU) and Distributed Unit (DU).  

---

## 🏗️ System Architecture
- **5G Core (OAI-CN)** → deployed via [`oai-cn5g-fed`](https://gitlab.eurecom.fr/oai/cn5g/oai-cn5g-fed.git)  
- **CU / DU / UE** → deployed via [`openairinterface5g`](https://gitlab.eurecom.fr/oai/openairinterface5g.git)  
- **Qtunnels** → PQC-enabled secure tunnels (QuNetSim, SimQN, NetSquid, SeQuence, SCTP)  
- **UE Authentication** → configured in MySQL database  

```mermaid
flowchart LR# Quantum-Ready OAI 5G Deployment with PQC Integration

## 📌 Abstract
The rise of quantum computing poses a major threat to traditional ciphers, specifically making the Radio Access Network (RAN) vulnerable to future quantum-based attacks.  

To address this challenge, this project proposes **Quantum-Inspired RAN (Q-RAN)** — a next-generation framework designed to future-proof telecom networks against quantum threats.  

As a foundation, we integrate **quantum network simulators** with the **OpenAirInterface (OAI) 5G stack** to deploy a standalone 5G network capable of supporting quantum operations. The integration introduces **Quantum Gateways (Qtunnels)** that secure the F1 interface between the Central Unit (CU) and Distributed Unit (DU).  

---

## 🏗️ System Architecture
- **5G Core (OAI-CN)** → deployed via [`oai-cn5g-fed`](https://gitlab.eurecom.fr/oai/cn5g/oai-cn5g-fed.git)  
- **CU / DU / UE** → deployed via [`openairinterface5g`](https://gitlab.eurecom.fr/oai/openairinterface5g.git)  
- **Qtunnels** → PQC-enabled secure tunnels (QuNetSim, SimQN, NetSquid, SeQuence, SCTP)  
- **UE Authentication** → configured in MySQL database  

```mermaid
flowchart LR
    subgraph Core["OAI 5G Core (Docker)"]
        AMF
        SMF
        UPF
        DN[(MySQL / Ext-DN)]
    end

    UE["UE (nr-uesoftmodem)"] <--> DU["DU (nr-softmodem)"]
    DU <--> QTUNNEL["Qtunnel (PQC/Quantum Sim)"]
    QTUNNEL <--> CU["CU (nr-softmodem)"]
    CU <--> Core

    subgraph Core["OAI 5G Core (Docker)"]
        AMF
        SMF
        UPF
        DN[(MySQL / Ext-DN)]
    end

    UE["UE (nr-uesoftmodem)"] <--> DU["DU (nr-softmodem)"]
    DU <--> QTUNNEL["Qtunnel (PQC/Quantum Sim)"]
    QTUNNEL <--> CU["CU (nr-softmodem)"]
    CU <--> Core
