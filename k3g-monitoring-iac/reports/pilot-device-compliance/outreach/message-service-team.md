# Message to Service Team

**To:** Service Team Lead
**Re:** Week 1 Metadata Collection — 4WNET-MNS-KTG-RX Service Candidates
**Deadline:** 2026-05-08 EOD
**Status:** Awaiting Response

---

Olá Service Team,

Como parte da fase de validação de service candidates no device 4WNET-MNS-KTG-RX, precisamos coletar metadados faltantes para 5 subinterfaces de serviço.

## O que precisamos

Preencher a planilha anexa com informações sobre cada subinterface:

| Subinterface | Campos Requeridos |
|---|---|
| Eth-Trunk0.10 | tenant, service_type, criticality, owner, evidence |
| Eth-Trunk0.147 | tenant, service_type, criticality, owner, evidence |
| Eth-Trunk0.1580 | tenant, service_type, criticality, owner, evidence |
| Eth-Trunk0.1589 | tenant, service_type, criticality, owner, evidence |
| Eth-Trunk0.1606 | tenant, service_type, criticality, owner, evidence |

## Definições

**tenant**
- Domínio de negócio ou cliente que utiliza a interface
- Exemplo: "core-network", "customer-vpn", "mpls-backbone"

**service_type**
- Tipo de serviço provisionado
- Valores aceitos: circuit, l3vpn, bgp, ospf, isis, static, wan-link, management
- Exemplo: "l3vpn"

**criticality**
- Impacto de indisponibilidade
- Valores: high (impacto crítico), medium (impacto médio), low (impacto baixo)
- Exemplo: "high"

**owner**
- Pessoa ou equipe responsável
- Formato: "Nome Sobrenome (email)"
- Exemplo: "João Silva (joao.silva@company.com)"

**evidence**
- Referência de documentação ou ticket
- Pode ser: link para documentação, número de ticket, referência de política
- Exemplo: "RFC-2024-001, Política de Serviços v3.2"

## Exemplo de Preenchimento

```
object_key,tenant,service_type,criticality,owner,evidence
Eth-Trunk0.10,core-network,l3vpn,high,João Silva (joao@company.com),RFC-2024-001
Eth-Trunk0.147,customer-vpn,circuit,medium,Maria Santos (maria@company.com),Ticket#5432
```

## Como Responder

1. **Receber arquivo:** service-team-response.csv (vazio, para preencher)
2. **Preencher:** Uma linha por subinterface
3. **Validar:**
   - Nenhum campo vazio
   - Nenhum caractere inválido (apenas ASCII)
   - Sem espaços desnecessários no início/fim
4. **Salvar:** Manter nome arquivo, manter formato CSV
5. **Enviar para:** reports/pilot-device-compliance/week1-responses/

## Prazo

**Crítico:** 2026-05-08 às 23:59 (EOD)

Respostas após esse prazo serão bloqueadas até a próxima fase.

## O Que Acontece Com a Resposta

Após receber:
1. Validação automática (formato, campos obrigatórios)
2. Revisão humana (valores válidos, consistência)
3. Se válido: avança para Week 2 review board
4. Se clarificação necessária: retornamos com feedback
5. Se bloqueado: investigação requerida

## Próximo Passo

Depois de validação, essas subinterfaces irão para:
- **Week 2 Review Board** (2026-05-09+): Revisão humana e risk assessment
- **Approval Records** (se aprovado): Agendamento para criação no NetBox

## Dúvidas

Entre em contato com K3G Team:
- **Lead:** [Name/Email]
- **Slack:** #k3g-inventory-sync
- **Docs:** reports/pilot-device-compliance/

## Attachments

- service-team-response.csv (template)
- week1-metadata-collection.md (descrição detalhada)
- service-owner-engagement-package.md (contexto da iniciativa)

---

Obrigado pela colaboração!

K3G Team
2026-04-29

