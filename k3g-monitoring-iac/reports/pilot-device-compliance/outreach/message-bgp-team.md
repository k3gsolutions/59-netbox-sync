# Message to BGP Team

**To:** BGP Team Lead
**Re:** Week 1 Metadata Collection — 4WNET-MNS-KTG-RX BGP Peer Enrichment
**Deadline:** 2026-05-08 EOD
**Status:** Awaiting Response

---

Olá BGP Team,

Como parte da fase de validação de service candidates no device 4WNET-MNS-KTG-RX, precisamos enriquecer informações sobre 1 peer BGP de serviço.

## O que precisamos

Preencher a planilha anexa com informações sobre o BGP peer:

| BGP Peer | Campos Requeridos |
|---|---|
| 203.0.113.1 | remote_asn, remote_bgp_group, owner, evidence |

## Definições

**remote_asn**
- Autonomous System Number do peer remoto
- Formato: número inteiro (1 a 4294967295)
- Exemplo: "65123", "12345"
- Deve estar documentado na política BGP

**remote_bgp_group**
- Grupo BGP ao qual o peer pertence
- Formato: "nome-grupo-bgp"
- Valores comuns: "customers", "providers", "internal", "peering", "backup"
- Exemplo: "customers", "provider-t1"

**owner**
- Pessoa ou equipe responsável pela configuração BGP
- Formato: "Nome Sobrenome (email)"
- Exemplo: "Alice Johnson (alice.johnson@company.com)"

**evidence**
- Referência de design ou documentação BGP
- Pode ser: link para BGP policy document, número de ticket, RFC/JunOS config
- Exemplo: "BGP-Policy-2024-v2.1, Ticket#3456"

## Exemplo de Preenchimento

```
object_key,remote_asn,remote_bgp_group,owner,evidence
203.0.113.1,65123,customers,Alice Johnson (alice@company.com),BGP-Policy-2024-v2.1
```

## Como Responder

1. **Receber arquivo:** bgp-team-response.csv (vazio, para preencher)
2. **Preencher:** Uma linha para o peer
3. **Validar:**
   - ASN deve ser válido (1-4294967295)
   - BGP group deve ser válido
   - Nenhum campo vazio
   - Sem caracteres inválidos (apenas ASCII)
4. **Salvar:** Manter nome arquivo, manter formato CSV
5. **Enviar para:** reports/pilot-device-compliance/week1-responses/

## Prazo

**Crítico:** 2026-05-08 às 23:59 (EOD)

Respostas após esse prazo serão bloqueadas até a próxima fase.

## O Que Acontece Com a Resposta

Após receber:
1. Validação automática (formato, campos obrigatórios)
2. Revisão de consistência (ASN válido? BGP group válido?)
3. Se válido: avança para Week 2 review board
4. Se clarificação necessária: retornamos com feedback
5. Se bloqueado: investigação requerida

## Próximo Passo

Depois de validação, esse peer irá para:
- **Week 2 Review Board** (2026-05-09+): Revisão humana e risk assessment
- **Approval Record** (se aprovado): Agendamento para criação/configuração no device

## Policy Considerations

- ASN deve estar registrado na organização
- BGP group deve corresponder ao design de rede
- Policy intent deve estar documentado
- Adjacency deve ser verificável (reachability)

## Dúvidas

Entre em contato com K3G Team:
- **Lead:** [Name/Email]
- **Slack:** #k3g-inventory-sync
- **Docs:** reports/pilot-device-compliance/

## Attachments

- bgp-team-response.csv (template)
- week1-metadata-collection.md (descrição detalhada)
- service-owner-engagement-package.md (contexto da iniciativa)

---

Obrigado pela colaboração!

K3G Team
2026-04-29

