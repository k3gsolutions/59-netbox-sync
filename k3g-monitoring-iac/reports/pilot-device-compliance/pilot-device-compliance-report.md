# Relatório de Compliance — 4WNET-MNS-KTG-RX
## 1. Resumo executivo
- Hostname: 4WNET-MNS-KTG-RX
- Device ID: 1890
- Modo: read-only
- NetBox carregado: Sim
- Compliance habilitado: Sim
- Status geral: drift_detected
- Total de divergências: 161
- Severidade mais alta: high

## 2. Sumário aplicado no dispositivo
| Métrica | Valor |
|---|---|
| Interfaces | 64 |
| IPs | 38 |
| VRFs | 2 |
| VLANs | 1 |
| Sessões BGP | 45 |
| Route policies | 163 |
| Prefix lists | 102 |
| AS-path filters | 34 |
| Communities | 190 |
| Community lists | 187 |

## 3. Sumário documentado no NetBox
| Métrica | Valor |
|---|---|
| Interfaces | 1 |
| IPs | 2 |
| VRFs | 1 |
| VLANs | 0 |
| Sessões BGP | 0 |
| Route policies | 140 |
| Prefix lists | 97 |
| AS-path filters | 0 |
| Communities | 229 |
| Community lists | 198 |

## 4. Diff agregado (por métrica)
| Métrica | Aplicado | Documentado | Delta | Status |
|---|---|---|---|---|
| interfaces | 64 | 1 | 63 | mismatch |
| ip_addresses | 38 | 2 | 36 | mismatch |
| vrfs | 2 | 1 | 1 | mismatch |
| vlans | 1 | 0 | 1 | mismatch |
| bgp_sessions | 45 | 0 | 45 | mismatch |
| route_policies | 163 | 140 | 23 | mismatch |
| prefix_lists | 102 | 97 | 5 | mismatch |
| as_path_filters | 34 | 0 | 34 | mismatch |
| communities | 190 | 229 | -39 | mismatch |
| community_lists | 187 | 198 | -11 | mismatch |

## 5. Divergências agregadas
| Severidade | Código | Escopo | Ação preferida | Mensagem |
|---|---|---|---|---|
| high | MISSING_IN_NETBOX | interfaces | fix_netbox | Existem objetos aplicados no dispositivo que não estão documentados no NetBox. |
| high | MISSING_IN_NETBOX | ip_addresses | fix_netbox | Existem objetos aplicados no dispositivo que não estão documentados no NetBox. |
| medium | MISSING_IN_NETBOX | vrfs | fix_netbox | Existem objetos aplicados no dispositivo que não estão documentados no NetBox. |
| medium | MISSING_IN_NETBOX | vlans | fix_netbox | Existem objetos aplicados no dispositivo que não estão documentados no NetBox. |
| high | MISSING_IN_NETBOX | bgp_sessions | fix_netbox | Existem objetos aplicados no dispositivo que não estão documentados no NetBox. |
| medium | MISSING_IN_NETBOX | route_policies | fix_netbox | Existem objetos aplicados no dispositivo que não estão documentados no NetBox. |
| medium | MISSING_IN_NETBOX | prefix_lists | fix_netbox | Existem objetos aplicados no dispositivo que não estão documentados no NetBox. |
| medium | MISSING_IN_NETBOX | as_path_filters | fix_netbox | Existem objetos aplicados no dispositivo que não estão documentados no NetBox. |
| medium | MISSING_ON_DEVICE | communities | review | Existem objetos documentados no NetBox que não aparecem no dispositivo. |
| medium | MISSING_ON_DEVICE | community_lists | review | Existem objetos documentados no NetBox que não aparecem no dispositivo. |

## 6. Divergências por objeto
| Severidade | Código | Tipo de objeto | Chave do objeto | Ação preferida | Mensagem |
|---|---|---|---|---|---|
| medium | INTERFACE_MISSING_IN_NETBOX | interface | Eth-Trunk0 | fix_netbox | Interface Eth-Trunk0 existe no dispositivo, mas não no NetBox. |
| medium | INTERFACE_MISSING_IN_NETBOX | interface | Eth-Trunk0.10 | fix_netbox | Interface Eth-Trunk0.10 existe no dispositivo, mas não no NetBox. |
| medium | INTERFACE_MISSING_IN_NETBOX | interface | Eth-Trunk0.147 | fix_netbox | Interface Eth-Trunk0.147 existe no dispositivo, mas não no NetBox. |
| medium | INTERFACE_MISSING_IN_NETBOX | interface | Eth-Trunk0.1580 | fix_netbox | Interface Eth-Trunk0.1580 existe no dispositivo, mas não no NetBox. |
| medium | INTERFACE_MISSING_IN_NETBOX | interface | Eth-Trunk0.1589 | fix_netbox | Interface Eth-Trunk0.1589 existe no dispositivo, mas não no NetBox. |
| medium | INTERFACE_MISSING_IN_NETBOX | interface | Eth-Trunk0.1606 | fix_netbox | Interface Eth-Trunk0.1606 existe no dispositivo, mas não no NetBox. |
| medium | INTERFACE_MISSING_IN_NETBOX | interface | Eth-Trunk0.2033 | fix_netbox | Interface Eth-Trunk0.2033 existe no dispositivo, mas não no NetBox. |
| medium | INTERFACE_MISSING_IN_NETBOX | interface | Eth-Trunk0.228 | fix_netbox | Interface Eth-Trunk0.228 existe no dispositivo, mas não no NetBox. |
| medium | INTERFACE_MISSING_IN_NETBOX | interface | Eth-Trunk0.2650 | fix_netbox | Interface Eth-Trunk0.2650 existe no dispositivo, mas não no NetBox. |
| medium | INTERFACE_MISSING_IN_NETBOX | interface | Eth-Trunk0.2651 | fix_netbox | Interface Eth-Trunk0.2651 existe no dispositivo, mas não no NetBox. |
| medium | INTERFACE_MISSING_IN_NETBOX | interface | Eth-Trunk0.2748 | fix_netbox | Interface Eth-Trunk0.2748 existe no dispositivo, mas não no NetBox. |
| medium | INTERFACE_MISSING_IN_NETBOX | interface | Eth-Trunk0.2749 | fix_netbox | Interface Eth-Trunk0.2749 existe no dispositivo, mas não no NetBox. |
| medium | INTERFACE_MISSING_IN_NETBOX | interface | Eth-Trunk0.3044 | fix_netbox | Interface Eth-Trunk0.3044 existe no dispositivo, mas não no NetBox. |
| medium | INTERFACE_MISSING_IN_NETBOX | interface | Eth-Trunk0.3065 | fix_netbox | Interface Eth-Trunk0.3065 existe no dispositivo, mas não no NetBox. |
| medium | INTERFACE_MISSING_IN_NETBOX | interface | Eth-Trunk0.3800 | fix_netbox | Interface Eth-Trunk0.3800 existe no dispositivo, mas não no NetBox. |
| medium | INTERFACE_MISSING_IN_NETBOX | interface | Eth-Trunk0.3801 | fix_netbox | Interface Eth-Trunk0.3801 existe no dispositivo, mas não no NetBox. |
| medium | INTERFACE_MISSING_IN_NETBOX | interface | Eth-Trunk0.3901 | fix_netbox | Interface Eth-Trunk0.3901 existe no dispositivo, mas não no NetBox. |
| medium | INTERFACE_MISSING_IN_NETBOX | interface | Eth-Trunk0.3902 | fix_netbox | Interface Eth-Trunk0.3902 existe no dispositivo, mas não no NetBox. |
| medium | INTERFACE_MISSING_IN_NETBOX | interface | Eth-Trunk0.3967 | fix_netbox | Interface Eth-Trunk0.3967 existe no dispositivo, mas não no NetBox. |
| medium | INTERFACE_MISSING_IN_NETBOX | interface | Eth-Trunk0.40 | fix_netbox | Interface Eth-Trunk0.40 existe no dispositivo, mas não no NetBox. |
| medium | INTERFACE_MISSING_IN_NETBOX | interface | Eth-Trunk0.4005 | fix_netbox | Interface Eth-Trunk0.4005 existe no dispositivo, mas não no NetBox. |
| medium | INTERFACE_MISSING_IN_NETBOX | interface | Eth-Trunk0.41 | fix_netbox | Interface Eth-Trunk0.41 existe no dispositivo, mas não no NetBox. |
| medium | INTERFACE_MISSING_IN_NETBOX | interface | Eth-Trunk0.43 | fix_netbox | Interface Eth-Trunk0.43 existe no dispositivo, mas não no NetBox. |
| medium | INTERFACE_MISSING_IN_NETBOX | interface | Eth-Trunk0.50 | fix_netbox | Interface Eth-Trunk0.50 existe no dispositivo, mas não no NetBox. |
| medium | INTERFACE_MISSING_IN_NETBOX | interface | Eth-Trunk0.51 | fix_netbox | Interface Eth-Trunk0.51 existe no dispositivo, mas não no NetBox. |
| medium | INTERFACE_MISSING_IN_NETBOX | interface | Eth-Trunk0.612 | fix_netbox | Interface Eth-Trunk0.612 existe no dispositivo, mas não no NetBox. |
| medium | INTERFACE_MISSING_IN_NETBOX | interface | Eth-Trunk0.652 | fix_netbox | Interface Eth-Trunk0.652 existe no dispositivo, mas não no NetBox. |
| medium | INTERFACE_MISSING_IN_NETBOX | interface | Eth-Trunk0.78 | fix_netbox | Interface Eth-Trunk0.78 existe no dispositivo, mas não no NetBox. |
| medium | INTERFACE_MISSING_IN_NETBOX | interface | Eth-Trunk0.801 | fix_netbox | Interface Eth-Trunk0.801 existe no dispositivo, mas não no NetBox. |
| medium | INTERFACE_MISSING_IN_NETBOX | interface | Eth-Trunk0.803 | fix_netbox | Interface Eth-Trunk0.803 existe no dispositivo, mas não no NetBox. |
| medium | INTERFACE_MISSING_IN_NETBOX | interface | Eth-Trunk0.805 | fix_netbox | Interface Eth-Trunk0.805 existe no dispositivo, mas não no NetBox. |
| medium | INTERFACE_MISSING_IN_NETBOX | interface | Eth-Trunk0.810 | fix_netbox | Interface Eth-Trunk0.810 existe no dispositivo, mas não no NetBox. |
| medium | INTERFACE_MISSING_IN_NETBOX | interface | Eth-Trunk0.811 | fix_netbox | Interface Eth-Trunk0.811 existe no dispositivo, mas não no NetBox. |
| medium | INTERFACE_MISSING_IN_NETBOX | interface | Eth-Trunk0.812 | fix_netbox | Interface Eth-Trunk0.812 existe no dispositivo, mas não no NetBox. |
| medium | INTERFACE_MISSING_IN_NETBOX | interface | Eth-Trunk0.817 | fix_netbox | Interface Eth-Trunk0.817 existe no dispositivo, mas não no NetBox. |
| medium | INTERFACE_MISSING_IN_NETBOX | interface | Eth-Trunk0.819 | fix_netbox | Interface Eth-Trunk0.819 existe no dispositivo, mas não no NetBox. |
| medium | INTERFACE_MISSING_IN_NETBOX | interface | Eth-Trunk0.827 | fix_netbox | Interface Eth-Trunk0.827 existe no dispositivo, mas não no NetBox. |
| medium | INTERFACE_MISSING_IN_NETBOX | interface | Eth-Trunk0.828 | fix_netbox | Interface Eth-Trunk0.828 existe no dispositivo, mas não no NetBox. |
| medium | INTERFACE_MISSING_IN_NETBOX | interface | Eth-Trunk0.895 | fix_netbox | Interface Eth-Trunk0.895 existe no dispositivo, mas não no NetBox. |
| medium | INTERFACE_MISSING_IN_NETBOX | interface | Eth-Trunk1 | fix_netbox | Interface Eth-Trunk1 existe no dispositivo, mas não no NetBox. |
| medium | INTERFACE_MISSING_IN_NETBOX | interface | Ethernet0/0/0 | fix_netbox | Interface Ethernet0/0/0 existe no dispositivo, mas não no NetBox. |
| medium | INTERFACE_MISSING_IN_NETBOX | interface | GigabitEthernet0/5/0 | fix_netbox | Interface GigabitEthernet0/5/0 existe no dispositivo, mas não no NetBox. |
| medium | INTERFACE_MISSING_IN_NETBOX | interface | GigabitEthernet0/5/1 | fix_netbox | Interface GigabitEthernet0/5/1 existe no dispositivo, mas não no NetBox. |
| medium | INTERFACE_MISSING_IN_NETBOX | interface | GigabitEthernet0/5/2 | fix_netbox | Interface GigabitEthernet0/5/2 existe no dispositivo, mas não no NetBox. |
| medium | INTERFACE_MISSING_IN_NETBOX | interface | GigabitEthernet0/5/3 | fix_netbox | Interface GigabitEthernet0/5/3 existe no dispositivo, mas não no NetBox. |
| medium | INTERFACE_MISSING_IN_NETBOX | interface | GigabitEthernet0/5/4 | fix_netbox | Interface GigabitEthernet0/5/4 existe no dispositivo, mas não no NetBox. |
| medium | INTERFACE_MISSING_IN_NETBOX | interface | GigabitEthernet0/5/5 | fix_netbox | Interface GigabitEthernet0/5/5 existe no dispositivo, mas não no NetBox. |
| medium | INTERFACE_MISSING_IN_NETBOX | interface | GigabitEthernet0/5/6(10G) | fix_netbox | Interface GigabitEthernet0/5/6(10G) existe no dispositivo, mas não no NetBox. |
| medium | INTERFACE_MISSING_IN_NETBOX | interface | GigabitEthernet0/5/7(10G) | fix_netbox | Interface GigabitEthernet0/5/7(10G) existe no dispositivo, mas não no NetBox. |
| medium | INTERFACE_MISSING_IN_NETBOX | interface | GigabitEthernet0/5/8(10G) | fix_netbox | Interface GigabitEthernet0/5/8(10G) existe no dispositivo, mas não no NetBox. |
| medium | INTERFACE_MISSING_IN_NETBOX | interface | GigabitEthernet0/5/9(10G) | fix_netbox | Interface GigabitEthernet0/5/9(10G) existe no dispositivo, mas não no NetBox. |
| medium | INTERFACE_MISSING_IN_NETBOX | interface | LoopBack0 | fix_netbox | Interface LoopBack0 existe no dispositivo, mas não no NetBox. |
| medium | INTERFACE_MISSING_IN_NETBOX | interface | LoopBack1 | fix_netbox | Interface LoopBack1 existe no dispositivo, mas não no NetBox. |
| medium | INTERFACE_MISSING_IN_NETBOX | interface | NULL0 | fix_netbox | Interface NULL0 existe no dispositivo, mas não no NetBox. |
| medium | INTERFACE_MISSING_IN_NETBOX | interface | Tunnel0 | fix_netbox | Interface Tunnel0 existe no dispositivo, mas não no NetBox. |
| medium | INTERFACE_MISSING_IN_NETBOX | interface | Tunnel1 | fix_netbox | Interface Tunnel1 existe no dispositivo, mas não no NetBox. |
| medium | INTERFACE_MISSING_IN_NETBOX | interface | Virtual-Ethernet0/2/100 | fix_netbox | Interface Virtual-Ethernet0/2/100 existe no dispositivo, mas não no NetBox. |
| medium | INTERFACE_MISSING_IN_NETBOX | interface | Virtual-Ethernet0/2/100.100 | fix_netbox | Interface Virtual-Ethernet0/2/100.100 existe no dispositivo, mas não no NetBox. |
| medium | INTERFACE_MISSING_IN_NETBOX | interface | Virtual-Ethernet0/2/101 | fix_netbox | Interface Virtual-Ethernet0/2/101 existe no dispositivo, mas não no NetBox. |
| medium | INTERFACE_MISSING_IN_NETBOX | interface | Virtual-Ethernet0/2/101.100 | fix_netbox | Interface Virtual-Ethernet0/2/101.100 existe no dispositivo, mas não no NetBox. |
| medium | INTERFACE_MISSING_IN_NETBOX | interface | Virtual-Ethernet0/2/200 | fix_netbox | Interface Virtual-Ethernet0/2/200 existe no dispositivo, mas não no NetBox. |
| medium | INTERFACE_MISSING_IN_NETBOX | interface | Virtual-Ethernet0/2/200.100 | fix_netbox | Interface Virtual-Ethernet0/2/200.100 existe no dispositivo, mas não no NetBox. |
| medium | INTERFACE_MISSING_IN_NETBOX | interface | Virtual-Ethernet0/2/201 | fix_netbox | Interface Virtual-Ethernet0/2/201 existe no dispositivo, mas não no NetBox. |
| medium | INTERFACE_MISSING_IN_NETBOX | interface | Virtual-Template0 | fix_netbox | Interface Virtual-Template0 existe no dispositivo, mas não no NetBox. |
| medium | INTERFACE_MISSING_ON_DEVICE | interface | eth0 | review | Interface eth0 existe no NetBox, mas não no dispositivo. |
| high | IP_MISSING_IN_NETBOX | ip_address | 10.20.0.13/30 | fix_netbox | IP 10.20.0.13/30 existe no dispositivo, mas não no NetBox. |
| high | IP_MISSING_IN_NETBOX | ip_address | 10.20.1.5/30 | fix_netbox | IP 10.20.1.5/30 existe no dispositivo, mas não no NetBox. |
| high | IP_MISSING_IN_NETBOX | ip_address | 10.20.255.5/30 | fix_netbox | IP 10.20.255.5/30 existe no dispositivo, mas não no NetBox. |
| high | IP_MISSING_IN_NETBOX | ip_address | 10.20.255.9/30 | fix_netbox | IP 10.20.255.9/30 existe no dispositivo, mas não no NetBox. |
| high | IP_MISSING_IN_NETBOX | ip_address | 10.200.1.255/32 | fix_netbox | IP 10.200.1.255/32 existe no dispositivo, mas não no NetBox. |
| high | IP_MISSING_IN_NETBOX | ip_address | 10.21.1.1/30 | fix_netbox | IP 10.21.1.1/30 existe no dispositivo, mas não no NetBox. |
| high | IP_MISSING_IN_NETBOX | ip_address | 10.21.1.5/30 | fix_netbox | IP 10.21.1.5/30 existe no dispositivo, mas não no NetBox. |
| high | IP_MISSING_IN_NETBOX | ip_address | 10.92.1.2/30 | fix_netbox | IP 10.92.1.2/30 existe no dispositivo, mas não no NetBox. |
| high | IP_MISSING_IN_NETBOX | ip_address | 10.92.1.6/30 | fix_netbox | IP 10.92.1.6/30 existe no dispositivo, mas não no NetBox. |
| high | IP_MISSING_IN_NETBOX | ip_address | 104.234.244.25/30 | fix_netbox | IP 104.234.244.25/30 existe no dispositivo, mas não no NetBox. |
| high | IP_MISSING_IN_NETBOX | ip_address | 104.234.244.29/30 | fix_netbox | IP 104.234.244.29/30 existe no dispositivo, mas não no NetBox. |
| high | IP_MISSING_IN_NETBOX | ip_address | 104.234.244.41/30 | fix_netbox | IP 104.234.244.41/30 existe no dispositivo, mas não no NetBox. |
| high | IP_MISSING_IN_NETBOX | ip_address | 104.234.244.9/29 | fix_netbox | IP 104.234.244.9/29 existe no dispositivo, mas não no NetBox. |
| high | IP_MISSING_IN_NETBOX | ip_address | 172.28.0.18/30 | fix_netbox | IP 172.28.0.18/30 existe no dispositivo, mas não no NetBox. |
| high | IP_MISSING_IN_NETBOX | ip_address | 172.28.0.21/30 | fix_netbox | IP 172.28.0.21/30 existe no dispositivo, mas não no NetBox. |
| high | IP_MISSING_IN_NETBOX | ip_address | 172.28.1.14/30 | fix_netbox | IP 172.28.1.14/30 existe no dispositivo, mas não no NetBox. |
| high | IP_MISSING_IN_NETBOX | ip_address | 172.28.1.17/30 | fix_netbox | IP 172.28.1.17/30 existe no dispositivo, mas não no NetBox. |
| high | IP_MISSING_IN_NETBOX | ip_address | 172.28.1.21/30 | fix_netbox | IP 172.28.1.21/30 existe no dispositivo, mas não no NetBox. |
| high | IP_MISSING_IN_NETBOX | ip_address | 172.28.1.25/30 | fix_netbox | IP 172.28.1.25/30 existe no dispositivo, mas não no NetBox. |
| high | IP_MISSING_IN_NETBOX | ip_address | 172.28.1.29/30 | fix_netbox | IP 172.28.1.29/30 existe no dispositivo, mas não no NetBox. |
| high | IP_MISSING_IN_NETBOX | ip_address | 172.28.1.33/30 | fix_netbox | IP 172.28.1.33/30 existe no dispositivo, mas não no NetBox. |
| high | IP_MISSING_IN_NETBOX | ip_address | 172.28.1.37/30 | fix_netbox | IP 172.28.1.37/30 existe no dispositivo, mas não no NetBox. |
| high | IP_MISSING_IN_NETBOX | ip_address | 172.28.1.45/30 | fix_netbox | IP 172.28.1.45/30 existe no dispositivo, mas não no NetBox. |
| high | IP_MISSING_IN_NETBOX | ip_address | 172.28.1.5/30 | fix_netbox | IP 172.28.1.5/30 existe no dispositivo, mas não no NetBox. |
| high | IP_MISSING_IN_NETBOX | ip_address | 172.28.1.53/30 | fix_netbox | IP 172.28.1.53/30 existe no dispositivo, mas não no NetBox. |
| high | IP_MISSING_IN_NETBOX | ip_address | 172.28.1.65/30 | fix_netbox | IP 172.28.1.65/30 existe no dispositivo, mas não no NetBox. |
| high | IP_MISSING_IN_NETBOX | ip_address | 172.28.1.77/30 | fix_netbox | IP 172.28.1.77/30 existe no dispositivo, mas não no NetBox. |
| high | IP_MISSING_IN_NETBOX | ip_address | 172.28.1.85/30 | fix_netbox | IP 172.28.1.85/30 existe no dispositivo, mas não no NetBox. |
| high | IP_MISSING_IN_NETBOX | ip_address | 172.28.1.89/30 | fix_netbox | IP 172.28.1.89/30 existe no dispositivo, mas não no NetBox. |
| high | IP_MISSING_IN_NETBOX | ip_address | 172.28.1.9/30 | fix_netbox | IP 172.28.1.9/30 existe no dispositivo, mas não no NetBox. |
| high | IP_MISSING_IN_NETBOX | ip_address | 172.28.1.93/30 | fix_netbox | IP 172.28.1.93/30 existe no dispositivo, mas não no NetBox. |
| high | IP_MISSING_IN_NETBOX | ip_address | 172.28.15.2/30 | fix_netbox | IP 172.28.15.2/30 existe no dispositivo, mas não no NetBox. |
| high | IP_MISSING_IN_NETBOX | ip_address | 187.16.198.13/24 | fix_netbox | IP 187.16.198.13/24 existe no dispositivo, mas não no NetBox. |
| high | IP_MISSING_IN_NETBOX | ip_address | 189.2.240.170/30 | fix_netbox | IP 189.2.240.170/30 existe no dispositivo, mas não no NetBox. |
| high | IP_MISSING_IN_NETBOX | ip_address | 192.168.0.1/24 | fix_netbox | IP 192.168.0.1/24 existe no dispositivo, mas não no NetBox. |
| high | IP_MISSING_IN_NETBOX | ip_address | 200.242.78.58/30 | fix_netbox | IP 200.242.78.58/30 existe no dispositivo, mas não no NetBox. |
| high | IP_MISSING_IN_NETBOX | ip_address | 45.68.75.137/21 | fix_netbox | IP 45.68.75.137/21 existe no dispositivo, mas não no NetBox. |
| medium | VRF_MISSING_ON_DEVICE | vrf | 4WNET | review | VRF 4WNET existe no NetBox, mas não no dispositivo. |
| medium | VRF_MISSING_IN_NETBOX | vrf | IX-MAO | fix_netbox | VRF IX-MAO existe no dispositivo, mas não no NetBox. |
| medium | VRF_MISSING_IN_NETBOX | vrf | __LOCAL_OAM_VPN__ | fix_netbox | VRF __LOCAL_OAM_VPN__ existe no dispositivo, mas não no NetBox. |
| medium | VLAN_MISSING_IN_NETBOX | vlan | 810 | fix_netbox | VLAN 810 existe no dispositivo, mas não no NetBox. |
| high | BGP_PEER_MISSING_IN_NETBOX | bgp_session | 10.20.0.14|ipv4 | fix_netbox | Sessão BGP 10.20.0.14|ipv4 existe no dispositivo, mas não no NetBox. |
| high | BGP_PEER_MISSING_IN_NETBOX | bgp_session | 10.20.1.2|ipv4 | fix_netbox | Sessão BGP 10.20.1.2|ipv4 existe no dispositivo, mas não no NetBox. |
| high | BGP_PEER_MISSING_IN_NETBOX | bgp_session | 10.20.1.6|ipv4 | fix_netbox | Sessão BGP 10.20.1.6|ipv4 existe no dispositivo, mas não no NetBox. |
| high | BGP_PEER_MISSING_IN_NETBOX | bgp_session | 10.20.255.10|ipv4 | fix_netbox | Sessão BGP 10.20.255.10|ipv4 existe no dispositivo, mas não no NetBox. |
| high | BGP_PEER_MISSING_IN_NETBOX | bgp_session | 10.20.255.6|ipv4 | fix_netbox | Sessão BGP 10.20.255.6|ipv4 existe no dispositivo, mas não no NetBox. |
| high | BGP_PEER_MISSING_IN_NETBOX | bgp_session | 104.234.244.30|ipv4 | fix_netbox | Sessão BGP 104.234.244.30|ipv4 existe no dispositivo, mas não no NetBox. |
| high | BGP_PEER_MISSING_IN_NETBOX | bgp_session | 172.28.1.13|ipv4 | fix_netbox | Sessão BGP 172.28.1.13|ipv4 existe no dispositivo, mas não no NetBox. |
| high | BGP_PEER_MISSING_IN_NETBOX | bgp_session | 172.28.1.18|ipv4 | fix_netbox | Sessão BGP 172.28.1.18|ipv4 existe no dispositivo, mas não no NetBox. |
| high | BGP_PEER_MISSING_IN_NETBOX | bgp_session | 172.28.1.34|ipv4 | fix_netbox | Sessão BGP 172.28.1.34|ipv4 existe no dispositivo, mas não no NetBox. |
| high | BGP_PEER_MISSING_IN_NETBOX | bgp_session | 172.28.1.54|ipv4 | fix_netbox | Sessão BGP 172.28.1.54|ipv4 existe no dispositivo, mas não no NetBox. |
| high | BGP_PEER_MISSING_IN_NETBOX | bgp_session | 172.28.1.66|ipv4 | fix_netbox | Sessão BGP 172.28.1.66|ipv4 existe no dispositivo, mas não no NetBox. |
| high | BGP_PEER_MISSING_IN_NETBOX | bgp_session | 172.28.1.6|ipv4 | fix_netbox | Sessão BGP 172.28.1.6|ipv4 existe no dispositivo, mas não no NetBox. |
| high | BGP_PEER_MISSING_IN_NETBOX | bgp_session | 172.28.1.74|ipv4 | fix_netbox | Sessão BGP 172.28.1.74|ipv4 existe no dispositivo, mas não no NetBox. |
| high | BGP_PEER_MISSING_IN_NETBOX | bgp_session | 172.28.1.78|ipv4 | fix_netbox | Sessão BGP 172.28.1.78|ipv4 existe no dispositivo, mas não no NetBox. |
| high | BGP_PEER_MISSING_IN_NETBOX | bgp_session | 172.28.1.86|ipv4 | fix_netbox | Sessão BGP 172.28.1.86|ipv4 existe no dispositivo, mas não no NetBox. |
| high | BGP_PEER_MISSING_IN_NETBOX | bgp_session | 172.28.1.90|ipv4 | fix_netbox | Sessão BGP 172.28.1.90|ipv4 existe no dispositivo, mas não no NetBox. |
| high | BGP_PEER_MISSING_IN_NETBOX | bgp_session | 172.28.1.94|ipv4 | fix_netbox | Sessão BGP 172.28.1.94|ipv4 existe no dispositivo, mas não no NetBox. |
| high | BGP_PEER_MISSING_IN_NETBOX | bgp_session | 189.2.240.169|ipv4 | fix_netbox | Sessão BGP 189.2.240.169|ipv4 existe no dispositivo, mas não no NetBox. |
| high | BGP_PEER_MISSING_IN_NETBOX | bgp_session | 200.242.78.57|ipv4 | fix_netbox | Sessão BGP 200.242.78.57|ipv4 existe no dispositivo, mas não no NetBox. |
| high | BGP_PEER_MISSING_IN_NETBOX | bgp_session | 2001:12F8:0:21::253|ipv6 | fix_netbox | Sessão BGP 2001:12F8:0:21::253|ipv6 existe no dispositivo, mas não no NetBox. |
| high | BGP_PEER_MISSING_IN_NETBOX | bgp_session | 2001:12F8:0:21::254|ipv6 | fix_netbox | Sessão BGP 2001:12F8:0:21::254|ipv6 existe no dispositivo, mas não no NetBox. |
| high | BGP_PEER_MISSING_IN_NETBOX | bgp_session | 2001:12F8:0:21::43|ipv6 | fix_netbox | Sessão BGP 2001:12F8:0:21::43|ipv6 existe no dispositivo, mas não no NetBox. |
| high | BGP_PEER_MISSING_IN_NETBOX | bgp_session | 2001:12F8:0:21::46|ipv6 | fix_netbox | Sessão BGP 2001:12F8:0:21::46|ipv6 existe no dispositivo, mas não no NetBox. |
| high | BGP_PEER_MISSING_IN_NETBOX | bgp_session | 2001:12F8:0:21::69|ipv6 | fix_netbox | Sessão BGP 2001:12F8:0:21::69|ipv6 existe no dispositivo, mas não no NetBox. |
| high | BGP_PEER_MISSING_IN_NETBOX | bgp_session | 2804:11B8:254::1|ipv6 | fix_netbox | Sessão BGP 2804:11B8:254::1|ipv6 existe no dispositivo, mas não no NetBox. |
| high | BGP_PEER_MISSING_IN_NETBOX | bgp_session | 2804:5984:B000:1::4E|ipv6 | fix_netbox | Sessão BGP 2804:5984:B000:1::4E|ipv6 existe no dispositivo, mas não no NetBox. |
| high | BGP_PEER_MISSING_IN_NETBOX | bgp_session | 2804:5984:B000:1::52|ipv6 | fix_netbox | Sessão BGP 2804:5984:B000:1::52|ipv6 existe no dispositivo, mas não no NetBox. |
| high | BGP_PEER_MISSING_IN_NETBOX | bgp_session | 2804:5984:B400:1::12|ipv6 | fix_netbox | Sessão BGP 2804:5984:B400:1::12|ipv6 existe no dispositivo, mas não no NetBox. |
| high | BGP_PEER_MISSING_IN_NETBOX | bgp_session | 2804:5984:B400:1::22|ipv6 | fix_netbox | Sessão BGP 2804:5984:B400:1::22|ipv6 existe no dispositivo, mas não no NetBox. |
| high | BGP_PEER_MISSING_IN_NETBOX | bgp_session | 2804:5984:B400:1::3A|ipv6 | fix_netbox | Sessão BGP 2804:5984:B400:1::3A|ipv6 existe no dispositivo, mas não no NetBox. |
| high | BGP_PEER_MISSING_IN_NETBOX | bgp_session | 2804:5984:B400:1::3E|ipv6 | fix_netbox | Sessão BGP 2804:5984:B400:1::3E|ipv6 existe no dispositivo, mas não no NetBox. |
| high | BGP_PEER_MISSING_IN_NETBOX | bgp_session | 2804:5984:B400:1::42|ipv6 | fix_netbox | Sessão BGP 2804:5984:B400:1::42|ipv6 existe no dispositivo, mas não no NetBox. |
| high | BGP_PEER_MISSING_IN_NETBOX | bgp_session | 2804:5984:B400:1::4E|ipv6 | fix_netbox | Sessão BGP 2804:5984:B400:1::4E|ipv6 existe no dispositivo, mas não no NetBox. |
| high | BGP_PEER_MISSING_IN_NETBOX | bgp_session | 2804:5984:B400:1::E|ipv6 | fix_netbox | Sessão BGP 2804:5984:B400:1::E|ipv6 existe no dispositivo, mas não no NetBox. |
| high | BGP_PEER_MISSING_IN_NETBOX | bgp_session | 2804:5984:B400:2::2|ipv6 | fix_netbox | Sessão BGP 2804:5984:B400:2::2|ipv6 existe no dispositivo, mas não no NetBox. |
| high | BGP_PEER_MISSING_IN_NETBOX | bgp_session | 2804:5984:B400:3::A|ipv6 | fix_netbox | Sessão BGP 2804:5984:B400:3::A|ipv6 existe no dispositivo, mas não no NetBox. |
| high | BGP_PEER_MISSING_IN_NETBOX | bgp_session | 2804:5984:B400::12|ipv6 | fix_netbox | Sessão BGP 2804:5984:B400::12|ipv6 existe no dispositivo, mas não no NetBox. |
| high | BGP_PEER_MISSING_IN_NETBOX | bgp_session | 2804:5984:B400::16|ipv6 | fix_netbox | Sessão BGP 2804:5984:B400::16|ipv6 existe no dispositivo, mas não no NetBox. |
| high | BGP_PEER_MISSING_IN_NETBOX | bgp_session | 2804:5984:B400::1A|ipv6 | fix_netbox | Sessão BGP 2804:5984:B400::1A|ipv6 existe no dispositivo, mas não no NetBox. |
| high | BGP_PEER_MISSING_IN_NETBOX | bgp_session | 2804:5984:B400::22|ipv6 | fix_netbox | Sessão BGP 2804:5984:B400::22|ipv6 existe no dispositivo, mas não no NetBox. |
| high | BGP_PEER_MISSING_IN_NETBOX | bgp_session | 2804:5984:B400::6|ipv6 | fix_netbox | Sessão BGP 2804:5984:B400::6|ipv6 existe no dispositivo, mas não no NetBox. |
| high | BGP_PEER_MISSING_IN_NETBOX | bgp_session | 2804:5984:B400::A|ipv6 | fix_netbox | Sessão BGP 2804:5984:B400::A|ipv6 existe no dispositivo, mas não no NetBox. |
| high | BGP_PEER_MISSING_IN_NETBOX | bgp_session | 2804:5984:BF04::2|ipv6 | fix_netbox | Sessão BGP 2804:5984:BF04::2|ipv6 existe no dispositivo, mas não no NetBox. |
| high | BGP_PEER_MISSING_IN_NETBOX | bgp_session | 2804:A8:2:A8::2FE5|ipv6 | fix_netbox | Sessão BGP 2804:A8:2:A8::2FE5|ipv6 existe no dispositivo, mas não no NetBox. |
| high | BGP_PEER_MISSING_IN_NETBOX | bgp_session | 2804:A8:2:A8::48C9|ipv6 | fix_netbox | Sessão BGP 2804:A8:2:A8::48C9|ipv6 existe no dispositivo, mas não no NetBox. |

## 7. Warnings
| Severidade | Código | Mensagem |
|---|---|---|
| info | NETBOX_BGP_PLUGIN_PARTIAL | Plugin NetBox BGP ausente/parcial: as_path_filter: The requested url: https://docs.k3gsolutions.com.br/api/plugins/bgp/as-path-filter/?limit=0 could not be found. |

## 8. Ações recomendadas
### Corrigir NetBox
- MISSING_IN_NETBOX — Existem objetos aplicados no dispositivo que não estão documentados no NetBox.
- INTERFACE_MISSING_IN_NETBOX (interface: Eth-Trunk0) — Interface Eth-Trunk0 existe no dispositivo, mas não no NetBox.
- INTERFACE_MISSING_IN_NETBOX (interface: Eth-Trunk0.10) — Interface Eth-Trunk0.10 existe no dispositivo, mas não no NetBox.
- INTERFACE_MISSING_IN_NETBOX (interface: Eth-Trunk0.147) — Interface Eth-Trunk0.147 existe no dispositivo, mas não no NetBox.
- INTERFACE_MISSING_IN_NETBOX (interface: Eth-Trunk0.1580) — Interface Eth-Trunk0.1580 existe no dispositivo, mas não no NetBox.
- INTERFACE_MISSING_IN_NETBOX (interface: Eth-Trunk0.1589) — Interface Eth-Trunk0.1589 existe no dispositivo, mas não no NetBox.
- INTERFACE_MISSING_IN_NETBOX (interface: Eth-Trunk0.1606) — Interface Eth-Trunk0.1606 existe no dispositivo, mas não no NetBox.
- INTERFACE_MISSING_IN_NETBOX (interface: Eth-Trunk0.2033) — Interface Eth-Trunk0.2033 existe no dispositivo, mas não no NetBox.
- INTERFACE_MISSING_IN_NETBOX (interface: Eth-Trunk0.228) — Interface Eth-Trunk0.228 existe no dispositivo, mas não no NetBox.
- INTERFACE_MISSING_IN_NETBOX (interface: Eth-Trunk0.2650) — Interface Eth-Trunk0.2650 existe no dispositivo, mas não no NetBox.
- INTERFACE_MISSING_IN_NETBOX (interface: Eth-Trunk0.2651) — Interface Eth-Trunk0.2651 existe no dispositivo, mas não no NetBox.
- INTERFACE_MISSING_IN_NETBOX (interface: Eth-Trunk0.2748) — Interface Eth-Trunk0.2748 existe no dispositivo, mas não no NetBox.
- INTERFACE_MISSING_IN_NETBOX (interface: Eth-Trunk0.2749) — Interface Eth-Trunk0.2749 existe no dispositivo, mas não no NetBox.
- INTERFACE_MISSING_IN_NETBOX (interface: Eth-Trunk0.3044) — Interface Eth-Trunk0.3044 existe no dispositivo, mas não no NetBox.
- INTERFACE_MISSING_IN_NETBOX (interface: Eth-Trunk0.3065) — Interface Eth-Trunk0.3065 existe no dispositivo, mas não no NetBox.
- INTERFACE_MISSING_IN_NETBOX (interface: Eth-Trunk0.3800) — Interface Eth-Trunk0.3800 existe no dispositivo, mas não no NetBox.
- INTERFACE_MISSING_IN_NETBOX (interface: Eth-Trunk0.3801) — Interface Eth-Trunk0.3801 existe no dispositivo, mas não no NetBox.
- INTERFACE_MISSING_IN_NETBOX (interface: Eth-Trunk0.3901) — Interface Eth-Trunk0.3901 existe no dispositivo, mas não no NetBox.
- INTERFACE_MISSING_IN_NETBOX (interface: Eth-Trunk0.3902) — Interface Eth-Trunk0.3902 existe no dispositivo, mas não no NetBox.
- INTERFACE_MISSING_IN_NETBOX (interface: Eth-Trunk0.3967) — Interface Eth-Trunk0.3967 existe no dispositivo, mas não no NetBox.
- INTERFACE_MISSING_IN_NETBOX (interface: Eth-Trunk0.40) — Interface Eth-Trunk0.40 existe no dispositivo, mas não no NetBox.
- INTERFACE_MISSING_IN_NETBOX (interface: Eth-Trunk0.4005) — Interface Eth-Trunk0.4005 existe no dispositivo, mas não no NetBox.
- INTERFACE_MISSING_IN_NETBOX (interface: Eth-Trunk0.41) — Interface Eth-Trunk0.41 existe no dispositivo, mas não no NetBox.
- INTERFACE_MISSING_IN_NETBOX (interface: Eth-Trunk0.43) — Interface Eth-Trunk0.43 existe no dispositivo, mas não no NetBox.
- INTERFACE_MISSING_IN_NETBOX (interface: Eth-Trunk0.50) — Interface Eth-Trunk0.50 existe no dispositivo, mas não no NetBox.
- INTERFACE_MISSING_IN_NETBOX (interface: Eth-Trunk0.51) — Interface Eth-Trunk0.51 existe no dispositivo, mas não no NetBox.
- INTERFACE_MISSING_IN_NETBOX (interface: Eth-Trunk0.612) — Interface Eth-Trunk0.612 existe no dispositivo, mas não no NetBox.
- INTERFACE_MISSING_IN_NETBOX (interface: Eth-Trunk0.652) — Interface Eth-Trunk0.652 existe no dispositivo, mas não no NetBox.
- INTERFACE_MISSING_IN_NETBOX (interface: Eth-Trunk0.78) — Interface Eth-Trunk0.78 existe no dispositivo, mas não no NetBox.
- INTERFACE_MISSING_IN_NETBOX (interface: Eth-Trunk0.801) — Interface Eth-Trunk0.801 existe no dispositivo, mas não no NetBox.
- INTERFACE_MISSING_IN_NETBOX (interface: Eth-Trunk0.803) — Interface Eth-Trunk0.803 existe no dispositivo, mas não no NetBox.
- INTERFACE_MISSING_IN_NETBOX (interface: Eth-Trunk0.805) — Interface Eth-Trunk0.805 existe no dispositivo, mas não no NetBox.
- INTERFACE_MISSING_IN_NETBOX (interface: Eth-Trunk0.810) — Interface Eth-Trunk0.810 existe no dispositivo, mas não no NetBox.
- INTERFACE_MISSING_IN_NETBOX (interface: Eth-Trunk0.811) — Interface Eth-Trunk0.811 existe no dispositivo, mas não no NetBox.
- INTERFACE_MISSING_IN_NETBOX (interface: Eth-Trunk0.812) — Interface Eth-Trunk0.812 existe no dispositivo, mas não no NetBox.
- INTERFACE_MISSING_IN_NETBOX (interface: Eth-Trunk0.817) — Interface Eth-Trunk0.817 existe no dispositivo, mas não no NetBox.
- INTERFACE_MISSING_IN_NETBOX (interface: Eth-Trunk0.819) — Interface Eth-Trunk0.819 existe no dispositivo, mas não no NetBox.
- INTERFACE_MISSING_IN_NETBOX (interface: Eth-Trunk0.827) — Interface Eth-Trunk0.827 existe no dispositivo, mas não no NetBox.
- INTERFACE_MISSING_IN_NETBOX (interface: Eth-Trunk0.828) — Interface Eth-Trunk0.828 existe no dispositivo, mas não no NetBox.
- INTERFACE_MISSING_IN_NETBOX (interface: Eth-Trunk0.895) — Interface Eth-Trunk0.895 existe no dispositivo, mas não no NetBox.
- INTERFACE_MISSING_IN_NETBOX (interface: Eth-Trunk1) — Interface Eth-Trunk1 existe no dispositivo, mas não no NetBox.
- INTERFACE_MISSING_IN_NETBOX (interface: Ethernet0/0/0) — Interface Ethernet0/0/0 existe no dispositivo, mas não no NetBox.
- INTERFACE_MISSING_IN_NETBOX (interface: GigabitEthernet0/5/0) — Interface GigabitEthernet0/5/0 existe no dispositivo, mas não no NetBox.
- INTERFACE_MISSING_IN_NETBOX (interface: GigabitEthernet0/5/1) — Interface GigabitEthernet0/5/1 existe no dispositivo, mas não no NetBox.
- INTERFACE_MISSING_IN_NETBOX (interface: GigabitEthernet0/5/2) — Interface GigabitEthernet0/5/2 existe no dispositivo, mas não no NetBox.
- INTERFACE_MISSING_IN_NETBOX (interface: GigabitEthernet0/5/3) — Interface GigabitEthernet0/5/3 existe no dispositivo, mas não no NetBox.
- INTERFACE_MISSING_IN_NETBOX (interface: GigabitEthernet0/5/4) — Interface GigabitEthernet0/5/4 existe no dispositivo, mas não no NetBox.
- INTERFACE_MISSING_IN_NETBOX (interface: GigabitEthernet0/5/5) — Interface GigabitEthernet0/5/5 existe no dispositivo, mas não no NetBox.
- INTERFACE_MISSING_IN_NETBOX (interface: GigabitEthernet0/5/6(10G)) — Interface GigabitEthernet0/5/6(10G) existe no dispositivo, mas não no NetBox.
- INTERFACE_MISSING_IN_NETBOX (interface: GigabitEthernet0/5/7(10G)) — Interface GigabitEthernet0/5/7(10G) existe no dispositivo, mas não no NetBox.
- INTERFACE_MISSING_IN_NETBOX (interface: GigabitEthernet0/5/8(10G)) — Interface GigabitEthernet0/5/8(10G) existe no dispositivo, mas não no NetBox.
- INTERFACE_MISSING_IN_NETBOX (interface: GigabitEthernet0/5/9(10G)) — Interface GigabitEthernet0/5/9(10G) existe no dispositivo, mas não no NetBox.
- INTERFACE_MISSING_IN_NETBOX (interface: LoopBack0) — Interface LoopBack0 existe no dispositivo, mas não no NetBox.
- INTERFACE_MISSING_IN_NETBOX (interface: LoopBack1) — Interface LoopBack1 existe no dispositivo, mas não no NetBox.
- INTERFACE_MISSING_IN_NETBOX (interface: NULL0) — Interface NULL0 existe no dispositivo, mas não no NetBox.
- INTERFACE_MISSING_IN_NETBOX (interface: Tunnel0) — Interface Tunnel0 existe no dispositivo, mas não no NetBox.
- INTERFACE_MISSING_IN_NETBOX (interface: Tunnel1) — Interface Tunnel1 existe no dispositivo, mas não no NetBox.
- INTERFACE_MISSING_IN_NETBOX (interface: Virtual-Ethernet0/2/100) — Interface Virtual-Ethernet0/2/100 existe no dispositivo, mas não no NetBox.
- INTERFACE_MISSING_IN_NETBOX (interface: Virtual-Ethernet0/2/100.100) — Interface Virtual-Ethernet0/2/100.100 existe no dispositivo, mas não no NetBox.
- INTERFACE_MISSING_IN_NETBOX (interface: Virtual-Ethernet0/2/101) — Interface Virtual-Ethernet0/2/101 existe no dispositivo, mas não no NetBox.
- INTERFACE_MISSING_IN_NETBOX (interface: Virtual-Ethernet0/2/101.100) — Interface Virtual-Ethernet0/2/101.100 existe no dispositivo, mas não no NetBox.
- INTERFACE_MISSING_IN_NETBOX (interface: Virtual-Ethernet0/2/200) — Interface Virtual-Ethernet0/2/200 existe no dispositivo, mas não no NetBox.
- INTERFACE_MISSING_IN_NETBOX (interface: Virtual-Ethernet0/2/200.100) — Interface Virtual-Ethernet0/2/200.100 existe no dispositivo, mas não no NetBox.
- INTERFACE_MISSING_IN_NETBOX (interface: Virtual-Ethernet0/2/201) — Interface Virtual-Ethernet0/2/201 existe no dispositivo, mas não no NetBox.
- INTERFACE_MISSING_IN_NETBOX (interface: Virtual-Template0) — Interface Virtual-Template0 existe no dispositivo, mas não no NetBox.
- IP_MISSING_IN_NETBOX (ip_address: 10.20.0.13/30) — IP 10.20.0.13/30 existe no dispositivo, mas não no NetBox.
- IP_MISSING_IN_NETBOX (ip_address: 10.20.1.5/30) — IP 10.20.1.5/30 existe no dispositivo, mas não no NetBox.
- IP_MISSING_IN_NETBOX (ip_address: 10.20.255.5/30) — IP 10.20.255.5/30 existe no dispositivo, mas não no NetBox.
- IP_MISSING_IN_NETBOX (ip_address: 10.20.255.9/30) — IP 10.20.255.9/30 existe no dispositivo, mas não no NetBox.
- IP_MISSING_IN_NETBOX (ip_address: 10.200.1.255/32) — IP 10.200.1.255/32 existe no dispositivo, mas não no NetBox.
- IP_MISSING_IN_NETBOX (ip_address: 10.21.1.1/30) — IP 10.21.1.1/30 existe no dispositivo, mas não no NetBox.
- IP_MISSING_IN_NETBOX (ip_address: 10.21.1.5/30) — IP 10.21.1.5/30 existe no dispositivo, mas não no NetBox.
- IP_MISSING_IN_NETBOX (ip_address: 10.92.1.2/30) — IP 10.92.1.2/30 existe no dispositivo, mas não no NetBox.
- IP_MISSING_IN_NETBOX (ip_address: 10.92.1.6/30) — IP 10.92.1.6/30 existe no dispositivo, mas não no NetBox.
- IP_MISSING_IN_NETBOX (ip_address: 104.234.244.25/30) — IP 104.234.244.25/30 existe no dispositivo, mas não no NetBox.
- IP_MISSING_IN_NETBOX (ip_address: 104.234.244.29/30) — IP 104.234.244.29/30 existe no dispositivo, mas não no NetBox.
- IP_MISSING_IN_NETBOX (ip_address: 104.234.244.41/30) — IP 104.234.244.41/30 existe no dispositivo, mas não no NetBox.
- IP_MISSING_IN_NETBOX (ip_address: 104.234.244.9/29) — IP 104.234.244.9/29 existe no dispositivo, mas não no NetBox.
- IP_MISSING_IN_NETBOX (ip_address: 172.28.0.18/30) — IP 172.28.0.18/30 existe no dispositivo, mas não no NetBox.
- IP_MISSING_IN_NETBOX (ip_address: 172.28.0.21/30) — IP 172.28.0.21/30 existe no dispositivo, mas não no NetBox.
- IP_MISSING_IN_NETBOX (ip_address: 172.28.1.14/30) — IP 172.28.1.14/30 existe no dispositivo, mas não no NetBox.
- IP_MISSING_IN_NETBOX (ip_address: 172.28.1.17/30) — IP 172.28.1.17/30 existe no dispositivo, mas não no NetBox.
- IP_MISSING_IN_NETBOX (ip_address: 172.28.1.21/30) — IP 172.28.1.21/30 existe no dispositivo, mas não no NetBox.
- IP_MISSING_IN_NETBOX (ip_address: 172.28.1.25/30) — IP 172.28.1.25/30 existe no dispositivo, mas não no NetBox.
- IP_MISSING_IN_NETBOX (ip_address: 172.28.1.29/30) — IP 172.28.1.29/30 existe no dispositivo, mas não no NetBox.
- IP_MISSING_IN_NETBOX (ip_address: 172.28.1.33/30) — IP 172.28.1.33/30 existe no dispositivo, mas não no NetBox.
- IP_MISSING_IN_NETBOX (ip_address: 172.28.1.37/30) — IP 172.28.1.37/30 existe no dispositivo, mas não no NetBox.
- IP_MISSING_IN_NETBOX (ip_address: 172.28.1.45/30) — IP 172.28.1.45/30 existe no dispositivo, mas não no NetBox.
- IP_MISSING_IN_NETBOX (ip_address: 172.28.1.5/30) — IP 172.28.1.5/30 existe no dispositivo, mas não no NetBox.
- IP_MISSING_IN_NETBOX (ip_address: 172.28.1.53/30) — IP 172.28.1.53/30 existe no dispositivo, mas não no NetBox.
- IP_MISSING_IN_NETBOX (ip_address: 172.28.1.65/30) — IP 172.28.1.65/30 existe no dispositivo, mas não no NetBox.
- IP_MISSING_IN_NETBOX (ip_address: 172.28.1.77/30) — IP 172.28.1.77/30 existe no dispositivo, mas não no NetBox.
- IP_MISSING_IN_NETBOX (ip_address: 172.28.1.85/30) — IP 172.28.1.85/30 existe no dispositivo, mas não no NetBox.
- IP_MISSING_IN_NETBOX (ip_address: 172.28.1.89/30) — IP 172.28.1.89/30 existe no dispositivo, mas não no NetBox.
- IP_MISSING_IN_NETBOX (ip_address: 172.28.1.9/30) — IP 172.28.1.9/30 existe no dispositivo, mas não no NetBox.
- IP_MISSING_IN_NETBOX (ip_address: 172.28.1.93/30) — IP 172.28.1.93/30 existe no dispositivo, mas não no NetBox.
- IP_MISSING_IN_NETBOX (ip_address: 172.28.15.2/30) — IP 172.28.15.2/30 existe no dispositivo, mas não no NetBox.
- IP_MISSING_IN_NETBOX (ip_address: 187.16.198.13/24) — IP 187.16.198.13/24 existe no dispositivo, mas não no NetBox.
- IP_MISSING_IN_NETBOX (ip_address: 189.2.240.170/30) — IP 189.2.240.170/30 existe no dispositivo, mas não no NetBox.
- IP_MISSING_IN_NETBOX (ip_address: 192.168.0.1/24) — IP 192.168.0.1/24 existe no dispositivo, mas não no NetBox.
- IP_MISSING_IN_NETBOX (ip_address: 200.242.78.58/30) — IP 200.242.78.58/30 existe no dispositivo, mas não no NetBox.
- IP_MISSING_IN_NETBOX (ip_address: 45.68.75.137/21) — IP 45.68.75.137/21 existe no dispositivo, mas não no NetBox.
- VRF_MISSING_IN_NETBOX (vrf: IX-MAO) — VRF IX-MAO existe no dispositivo, mas não no NetBox.
- VRF_MISSING_IN_NETBOX (vrf: __LOCAL_OAM_VPN__) — VRF __LOCAL_OAM_VPN__ existe no dispositivo, mas não no NetBox.
- VLAN_MISSING_IN_NETBOX (vlan: 810) — VLAN 810 existe no dispositivo, mas não no NetBox.
- BGP_PEER_MISSING_IN_NETBOX (bgp_session: 10.20.0.14|ipv4) — Sessão BGP 10.20.0.14|ipv4 existe no dispositivo, mas não no NetBox.
- BGP_PEER_MISSING_IN_NETBOX (bgp_session: 10.20.1.2|ipv4) — Sessão BGP 10.20.1.2|ipv4 existe no dispositivo, mas não no NetBox.
- BGP_PEER_MISSING_IN_NETBOX (bgp_session: 10.20.1.6|ipv4) — Sessão BGP 10.20.1.6|ipv4 existe no dispositivo, mas não no NetBox.
- BGP_PEER_MISSING_IN_NETBOX (bgp_session: 10.20.255.10|ipv4) — Sessão BGP 10.20.255.10|ipv4 existe no dispositivo, mas não no NetBox.
- BGP_PEER_MISSING_IN_NETBOX (bgp_session: 10.20.255.6|ipv4) — Sessão BGP 10.20.255.6|ipv4 existe no dispositivo, mas não no NetBox.
- BGP_PEER_MISSING_IN_NETBOX (bgp_session: 104.234.244.30|ipv4) — Sessão BGP 104.234.244.30|ipv4 existe no dispositivo, mas não no NetBox.
- BGP_PEER_MISSING_IN_NETBOX (bgp_session: 172.28.1.13|ipv4) — Sessão BGP 172.28.1.13|ipv4 existe no dispositivo, mas não no NetBox.
- BGP_PEER_MISSING_IN_NETBOX (bgp_session: 172.28.1.18|ipv4) — Sessão BGP 172.28.1.18|ipv4 existe no dispositivo, mas não no NetBox.
- BGP_PEER_MISSING_IN_NETBOX (bgp_session: 172.28.1.34|ipv4) — Sessão BGP 172.28.1.34|ipv4 existe no dispositivo, mas não no NetBox.
- BGP_PEER_MISSING_IN_NETBOX (bgp_session: 172.28.1.54|ipv4) — Sessão BGP 172.28.1.54|ipv4 existe no dispositivo, mas não no NetBox.
- BGP_PEER_MISSING_IN_NETBOX (bgp_session: 172.28.1.66|ipv4) — Sessão BGP 172.28.1.66|ipv4 existe no dispositivo, mas não no NetBox.
- BGP_PEER_MISSING_IN_NETBOX (bgp_session: 172.28.1.6|ipv4) — Sessão BGP 172.28.1.6|ipv4 existe no dispositivo, mas não no NetBox.
- BGP_PEER_MISSING_IN_NETBOX (bgp_session: 172.28.1.74|ipv4) — Sessão BGP 172.28.1.74|ipv4 existe no dispositivo, mas não no NetBox.
- BGP_PEER_MISSING_IN_NETBOX (bgp_session: 172.28.1.78|ipv4) — Sessão BGP 172.28.1.78|ipv4 existe no dispositivo, mas não no NetBox.
- BGP_PEER_MISSING_IN_NETBOX (bgp_session: 172.28.1.86|ipv4) — Sessão BGP 172.28.1.86|ipv4 existe no dispositivo, mas não no NetBox.
- BGP_PEER_MISSING_IN_NETBOX (bgp_session: 172.28.1.90|ipv4) — Sessão BGP 172.28.1.90|ipv4 existe no dispositivo, mas não no NetBox.
- BGP_PEER_MISSING_IN_NETBOX (bgp_session: 172.28.1.94|ipv4) — Sessão BGP 172.28.1.94|ipv4 existe no dispositivo, mas não no NetBox.
- BGP_PEER_MISSING_IN_NETBOX (bgp_session: 189.2.240.169|ipv4) — Sessão BGP 189.2.240.169|ipv4 existe no dispositivo, mas não no NetBox.
- BGP_PEER_MISSING_IN_NETBOX (bgp_session: 200.242.78.57|ipv4) — Sessão BGP 200.242.78.57|ipv4 existe no dispositivo, mas não no NetBox.
- BGP_PEER_MISSING_IN_NETBOX (bgp_session: 2001:12F8:0:21::253|ipv6) — Sessão BGP 2001:12F8:0:21::253|ipv6 existe no dispositivo, mas não no NetBox.
- BGP_PEER_MISSING_IN_NETBOX (bgp_session: 2001:12F8:0:21::254|ipv6) — Sessão BGP 2001:12F8:0:21::254|ipv6 existe no dispositivo, mas não no NetBox.
- BGP_PEER_MISSING_IN_NETBOX (bgp_session: 2001:12F8:0:21::43|ipv6) — Sessão BGP 2001:12F8:0:21::43|ipv6 existe no dispositivo, mas não no NetBox.
- BGP_PEER_MISSING_IN_NETBOX (bgp_session: 2001:12F8:0:21::46|ipv6) — Sessão BGP 2001:12F8:0:21::46|ipv6 existe no dispositivo, mas não no NetBox.
- BGP_PEER_MISSING_IN_NETBOX (bgp_session: 2001:12F8:0:21::69|ipv6) — Sessão BGP 2001:12F8:0:21::69|ipv6 existe no dispositivo, mas não no NetBox.
- BGP_PEER_MISSING_IN_NETBOX (bgp_session: 2804:11B8:254::1|ipv6) — Sessão BGP 2804:11B8:254::1|ipv6 existe no dispositivo, mas não no NetBox.
- BGP_PEER_MISSING_IN_NETBOX (bgp_session: 2804:5984:B000:1::4E|ipv6) — Sessão BGP 2804:5984:B000:1::4E|ipv6 existe no dispositivo, mas não no NetBox.
- BGP_PEER_MISSING_IN_NETBOX (bgp_session: 2804:5984:B000:1::52|ipv6) — Sessão BGP 2804:5984:B000:1::52|ipv6 existe no dispositivo, mas não no NetBox.
- BGP_PEER_MISSING_IN_NETBOX (bgp_session: 2804:5984:B400:1::12|ipv6) — Sessão BGP 2804:5984:B400:1::12|ipv6 existe no dispositivo, mas não no NetBox.
- BGP_PEER_MISSING_IN_NETBOX (bgp_session: 2804:5984:B400:1::22|ipv6) — Sessão BGP 2804:5984:B400:1::22|ipv6 existe no dispositivo, mas não no NetBox.
- BGP_PEER_MISSING_IN_NETBOX (bgp_session: 2804:5984:B400:1::3A|ipv6) — Sessão BGP 2804:5984:B400:1::3A|ipv6 existe no dispositivo, mas não no NetBox.
- BGP_PEER_MISSING_IN_NETBOX (bgp_session: 2804:5984:B400:1::3E|ipv6) — Sessão BGP 2804:5984:B400:1::3E|ipv6 existe no dispositivo, mas não no NetBox.
- BGP_PEER_MISSING_IN_NETBOX (bgp_session: 2804:5984:B400:1::42|ipv6) — Sessão BGP 2804:5984:B400:1::42|ipv6 existe no dispositivo, mas não no NetBox.
- BGP_PEER_MISSING_IN_NETBOX (bgp_session: 2804:5984:B400:1::4E|ipv6) — Sessão BGP 2804:5984:B400:1::4E|ipv6 existe no dispositivo, mas não no NetBox.
- BGP_PEER_MISSING_IN_NETBOX (bgp_session: 2804:5984:B400:1::E|ipv6) — Sessão BGP 2804:5984:B400:1::E|ipv6 existe no dispositivo, mas não no NetBox.
- BGP_PEER_MISSING_IN_NETBOX (bgp_session: 2804:5984:B400:2::2|ipv6) — Sessão BGP 2804:5984:B400:2::2|ipv6 existe no dispositivo, mas não no NetBox.
- BGP_PEER_MISSING_IN_NETBOX (bgp_session: 2804:5984:B400:3::A|ipv6) — Sessão BGP 2804:5984:B400:3::A|ipv6 existe no dispositivo, mas não no NetBox.
- BGP_PEER_MISSING_IN_NETBOX (bgp_session: 2804:5984:B400::12|ipv6) — Sessão BGP 2804:5984:B400::12|ipv6 existe no dispositivo, mas não no NetBox.
- BGP_PEER_MISSING_IN_NETBOX (bgp_session: 2804:5984:B400::16|ipv6) — Sessão BGP 2804:5984:B400::16|ipv6 existe no dispositivo, mas não no NetBox.
- BGP_PEER_MISSING_IN_NETBOX (bgp_session: 2804:5984:B400::1A|ipv6) — Sessão BGP 2804:5984:B400::1A|ipv6 existe no dispositivo, mas não no NetBox.
- BGP_PEER_MISSING_IN_NETBOX (bgp_session: 2804:5984:B400::22|ipv6) — Sessão BGP 2804:5984:B400::22|ipv6 existe no dispositivo, mas não no NetBox.
- BGP_PEER_MISSING_IN_NETBOX (bgp_session: 2804:5984:B400::6|ipv6) — Sessão BGP 2804:5984:B400::6|ipv6 existe no dispositivo, mas não no NetBox.
- BGP_PEER_MISSING_IN_NETBOX (bgp_session: 2804:5984:B400::A|ipv6) — Sessão BGP 2804:5984:B400::A|ipv6 existe no dispositivo, mas não no NetBox.
- BGP_PEER_MISSING_IN_NETBOX (bgp_session: 2804:5984:BF04::2|ipv6) — Sessão BGP 2804:5984:BF04::2|ipv6 existe no dispositivo, mas não no NetBox.
- BGP_PEER_MISSING_IN_NETBOX (bgp_session: 2804:A8:2:A8::2FE5|ipv6) — Sessão BGP 2804:A8:2:A8::2FE5|ipv6 existe no dispositivo, mas não no NetBox.
- BGP_PEER_MISSING_IN_NETBOX (bgp_session: 2804:A8:2:A8::48C9|ipv6) — Sessão BGP 2804:A8:2:A8::48C9|ipv6 existe no dispositivo, mas não no NetBox.

### Corrigir equipamento
- Nenhuma ação recomendada.

### Revisão manual
- MISSING_ON_DEVICE — Existem objetos documentados no NetBox que não aparecem no dispositivo.
- INTERFACE_MISSING_ON_DEVICE (interface: eth0) — Interface eth0 existe no NetBox, mas não no dispositivo.
- VRF_MISSING_ON_DEVICE (vrf: 4WNET) — VRF 4WNET existe no NetBox, mas não no dispositivo.

## 9. Observações de segurança
- Relatório gerado em modo read-only.
- Nenhuma escrita no NetBox.
- Nenhuma configuração aplicada no dispositivo.
- /sync não foi usado neste relatório.
- Comandos futuros exigem aprovação humana antes de execução.
