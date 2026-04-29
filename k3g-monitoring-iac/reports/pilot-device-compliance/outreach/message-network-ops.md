# Message to Network Ops

**To:** Network Ops Lead
**Re:** Week 1 Metadata Collection — 4WNET-MNS-KTG-RX IP Address Enrichment
**Deadline:** 2026-05-08 EOD
**Status:** Awaiting Response

---

Olá Network Ops,

Como parte da fase de validação de service candidates no device 4WNET-MNS-KTG-RX, precisamos enriquecer informações sobre 1 endereço IP de serviço.

## O que precisamos

Preencher a planilha anexa com informações sobre o IP address:

| IP Address | Campos Requeridos |
|---|---|
| 192.0.2.1/30 | interface, vrf, owner, evidence |

## Definições

**interface**
- Interface física ou lógica onde o IP está configurado
- Formato: "nome-interface" (exemplo: "Eth0/0/1", "Vlan100")
- Deve existir no device

**vrf**
- VRF (Virtual Routing and Forwarding) context
- Formato: "nome-vrf" ou "default"
- Exemplo: "prod-vpn", "default", "mgmt-vrf"
- Deve corresponder ao design de routing do device

**owner**
- Pessoa ou equipe responsável pela configuração
- Formato: "Nome Sobrenome (email)"
- Exemplo: "Pedro Costa (pedro.costa@company.com)"

**evidence**
- Referência de design ou documentação
- Pode ser: link para design document, número de ticket, referência de política
- Exemplo: "Design-IP-2024-v1.2, Ticket#9876"

## Exemplo de Preenchimento

```
object_key,interface,vrf,owner,evidence
192.0.2.1/30,Eth0/0/1,prod-vpn,Pedro Costa (pedro@company.com),Design-IP-2024-v1.2
```

## Como Responder

1. **Receber arquivo:** network-ops-response.csv (vazio, para preencher)
2. **Preencher:** Uma linha para o IP
3. **Validar:**
   - Interface deve existir no device (ou ser esperada)
   - VRF deve ser válido (ou default)
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
2. Revisão de consistência (interface + VRF válidos?)
3. Se válido: avança para Week 2 review board
4. Se clarificação necessária: retornamos com feedback
5. Se bloqueado: investigação requerida

## Próximo Passo

Depois de validação, esse IP irá para:
- **Week 2 Review Board** (2026-05-09+): Revisão humana e risk assessment
- **Approval Record** (se aprovado): Agendamento para criação/atualização no NetBox

## Dúvidas

Entre em contato com K3G Team:
- **Lead:** [Name/Email]
- **Slack:** #k3g-inventory-sync
- **Docs:** reports/pilot-device-compliance/

## Attachments

- network-ops-response.csv (template)
- week1-metadata-collection.md (descrição detalhada)
- service-owner-engagement-package.md (contexto da iniciativa)

---

Obrigado pela colaboração!

K3G Team
2026-04-29

