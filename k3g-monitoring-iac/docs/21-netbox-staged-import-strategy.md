# NetBox Staged Import Strategy

## Princípio

NetBox continua sendo Source of Truth.

Dispositivo gera evidência, não verdade automática.

O fluxo de importação assistida existe apenas para acelerar brownfield, backfill e saneamento documental.

## Objetivo

Gerar propostas de enriquecimento do NetBox a partir do DeviceInventory, com aprovação humana.

A escrita futura no NetBox deve ser controlada, auditável, reversível quando possível e sempre subordinada ao compliance.

## Fluxo

1. Coletar DeviceInventory.
2. Carregar NetBoxInventory.
3. Gerar diff.
4. Criar ImportPlan.
5. Classificar ações:
   - safe_create_staged
   - needs_review
   - blocked
   - ignore
6. Humano revisa.
7. Humano aprova.
8. Aplicar no NetBox com status/tag staged, quando permitido.
9. Reexecutar compliance.

## Regra obrigatória de nomenclatura

Qualquer objeto detectado no dispositivo que não atender à convenção oficial de nomenclatura deve ser bloqueado para importação automática.

Ação:

- Não criar no NetBox.
- Não criar como staged.
- Não atualizar objeto existente.
- Classificar como needs_review.
- Registrar no relatório de compliance.
- Exigir revisão humana.

Exemplo:

Se a descrição/interface/serviço não seguir:

`<service_type>:<tenant_slug>:NB-<id>[:extra]`

então a proposta deve ser:

- action: needs_review
- reason: naming_convention_failed
- preferred_action: review
- report_section: Revisão humana obrigatória

## Regra de ouro

Criar pode ser permitido como staged apenas quando:

- objeto passa na convenção de nomenclatura;
- matching não é ambíguo;
- tenant é identificado;
- service_type é identificado;
- criticality é identificada ou herdada;
- objeto não conflita com design já existente no NetBox;
- aprovação humana foi registrada.

Atualizar existente exige revisão.

Deletar nunca automático.

## Classificação das ações

### safe_create_staged

Pode virar proposta de criação staged no NetBox.

Requisitos:

- naming convention válida;
- matching confidence exact ou normalized;
- tenant identificado;
- service_type identificado;
- sem conflito com objeto existente;
- dados mínimos presentes;
- aprovado por humano.

### needs_review

Não pode ser escrito automaticamente.

Usar quando:

- naming convention ausente ou inválida;
- tenant ausente;
- service_type ausente;
- criticality ausente;
- objeto existente diverge;
- BGP peer sem description;
- policy ambígua;
- relação interface/IP/VRF incerta;
- múltiplos matches possíveis;
- objeto parece temporário;
- objeto está fora de Established, no caso de BGP.

### blocked

Não pode ser importado.

Usar quando:

- matching ambíguo grave;
- objeto pode sobrescrever design correto;
- objeto contém dados insuficientes;
- objeto parece legado sem dono;
- objeto conflita com múltiplos tenants;
- operação exigiria delete;
- operação exigiria alteração de objeto active existente.

### ignore

Usar quando:

- objeto é operacional/temporário;
- interface sem relevância de monitoramento;
- loopback interna não monitorável;
- objeto explicitamente excluído por política.

## Regras de escrita futura

- Criar pode ser permitido como staged.
- Atualizar existente exige revisão.
- Deletar nunca automático.
- Matching ambíguo bloqueia escrita.
- Objeto sem tenant/service_type/criticality bloqueia escrita.
- Objeto fora da naming convention não é importado.
- Objeto fora da naming convention vai para revisão humana.
- Objeto fora da naming convention deve aparecer no relatório.
- Token de escrita separado do token read-only.
- Dry-run obrigatório.
- Audit log obrigatório.
- Aprovação humana obrigatória.
- Nunca promover staged para active automaticamente.

## Tags sugeridas

- discovery:netops_netbox_sync
- discovery:staged
- discovery:needs-review
- discovery:from-device
- compliance:drift
- source:device
- naming:non-compliant
- approval:pending

## Custom fields sugeridos

- discovery_source
- discovery_timestamp
- discovery_confidence
- discovery_status
- discovery_reason
- approved_by
- approved_at
- import_plan_id

## Objetos candidatos

### Primeira fase

- interfaces
- IPs
- VLANs
- VRFs

### Fase posterior

- BGP sessions
- routing policies
- prefix lists
- community lists
- circuits
- L2VPN

## Objetos que exigem revisão humana sempre

- objetos sem naming convention válida;
- BGP peers sem description;
- interfaces sem tenant;
- interfaces sem service_type;
- circuits sem tenant;
- objects com matching ambíguo;
- objetos com conflito de VRF/VLAN/IP;
- qualquer atualização em objeto já existente;
- qualquer mudança que possa afetar monitoramento de cliente ativo.

## Relatório

O relatório deve ter uma seção:

## Revisão humana obrigatória

Com colunas:

- object_type
- object_key
- reason
- evidence
- recommended_action

Exemplos de reason:

- naming_convention_failed
- tenant_missing
- service_type_missing
- ambiguous_match
- bgp_peer_without_description
- existing_object_conflict
- insufficient_metadata

## Riscos

- documentar caos;
- duplicidade;
- sobrescrever design correto;
- enfraquecer NetBox como SoT;
- importação permanente virar anti-pattern;
- promover configuração temporária para documentação oficial;
- cadastrar objeto sem dono;
- cadastrar objeto com tenant errado.

## Mitigações

- staged/planned;
- aprovação humana;
- dry-run;
- audit log;
- matching confidence;
- rollback plan;
- nunca deletar automaticamente;
- nunca importar objeto fora da naming convention;
- relatório obrigatório de revisão humana;
- token separado para escrita;
- permissões mínimas.

## Fora de escopo agora

- escrita automática;
- sync permanente device -> NetBox;
- aplicar config em equipamento;
- substituir design-first;
- promover staged para active automaticamente;
- corrigir naming no equipamento automaticamente.
