# Comparativo de Compliance — 4WNET-MNS-KTG-RX
## 1. Resumo
- Relatório anterior: report-old.md
- Relatório novo: report-new.md
- Total anterior: 3 divergências
- Total agora: 2 divergências
- Delta: -1
- Status anterior: drift_detected
- Status agora: drift_detected

## 2. Evolução por severidade
| Severidade | Antes | Agora | Delta |
|---|---|---|---|
| --- | 2 | 2 | +0 |
| low | 1 | 1 | +0 |
| medium | 2 | 1 | -1 |

## 3. Novas divergências
| Severidade | Código | Tipo | Chave | Ação | Mensagem |
|---|---|---|---|---|---|
| low | VRF_MISMATCH | vrf | VRF-PROD | review | VRF-PROD tem configurações divergentes. |

## 4. Divergências resolvidas
| Severidade | Código | Tipo | Chave | Ação | Mensagem |
|---|---|---|---|---|---|
| low | MISSING_IN_NETBOX | None | None | review | 1 interface no dispositivo não está no NetBox. |
| medium | IP_MISSING_IN_NETBOX | ip_address | 10.0.0.1/24 | fix_netbox | IP 10.0.0.1/24 não documentado. |

## 5. Divergências recorrentes (ainda não resolvidas)
| Severidade | Código | Tipo | Chave | Ação | Mensagem |
|---|---|---|---|---|---|
| --- | --- | None | None | --- | --- |
| --- | --- | --- | --- | --- | --- |
| medium | INTERFACE_MISSING_IN_NETBOX | interface | Eth-Trunk0 | fix_netbox | Interface Eth-Trunk0 existe no dispositivo, mas não no NetBox. |

## 6. Observações
- Comparação baseada em análise local de Markdown.
- Nenhuma API real chamada.
- Nenhum raw JSON utilizado.
- Nenhuma escrita no NetBox.
- Nenhuma alteração em equipamento.
- Chave de divergência: (code, object_type, object_key, scope).
