# NetOps NetBox Sync

Contexto de automacao de compliance de rede que consulta o NetBox, coleta dados read-only de dispositivos e compara evidencias coletadas com politicas operacionais.

## Language

**Compliance Guiado**:
Fluxo interativo em que um operador escolhe cliente, dispositivo e contextos de analise antes de executar verificacoes read-only.
_Avoid_: tela de layout, wizard generico

**Candidato de Compliance**:
Dispositivo ativo no NetBox elegivel para analise de compliance conforme filtros operacionais do projeto.
_Avoid_: device qualquer, ativo qualquer

**Contexto de Analise**:
Recorte funcional de compliance que determina qual fonte de evidencia sera consultada, como interfaces, BGP, seguranca, NTP/SNMP ou sysname.
_Avoid_: aba, card, categoria visual

**Coleta Read-only**:
Obtencao de evidencias do dispositivo por SSH ou SNMP sem aplicar configuracao e sem escrita no NetBox.
_Avoid_: sync, deploy, real write

**Job de Compliance**:
Registro local de uma execucao controlada de compliance com gates, plano de coleta, artefatos coletados, parser e comparacao.
_Avoid_: analise solta, request isolada

**Parser Local**:
Processamento local dos artefatos coletados para produzir inventario estruturado antes da comparacao de compliance.
_Avoid_: coleta, validacao visual

## Relationships

- Um **Compliance Guiado** seleciona exatamente um **Candidato de Compliance** por analise.
- Um **Compliance Guiado** executa um ou mais **Contextos de Analise**.
- Um **Contexto de Analise** pode depender de dados do NetBox, de **Coleta Read-only** por SSH ou de **Coleta Read-only** por SNMP.
- Um **Job de Compliance** pode produzir uma **Coleta Read-only**, um **Parser Local** e uma comparacao de compliance.
- Um **Parser Local** depende de artefatos de **Coleta Read-only** ja persistidos.

## Example dialogue

> **Dev:** "Quando o operador seleciona BGP no **Compliance Guiado**, isso e apenas um card visual?"
> **Domain expert:** "Nao. BGP e um **Contexto de Analise** e exige evidencia do dispositivo; se usarmos o painel integrado, ele deve resolver credenciais e executar **Coleta Read-only** por SSH."

**Inventário Local (Cache Operacional)**:
Banco de dados local (SQLite fase 1, Postgres depois) que replica subconjunto crítico do NetBox: tenants, devices, credenciais, snmp_community. Permite compliance sem depender sempre do NetBox.

**Análise Avulsa (Modo Arquivo)**:
Fluxo alternativo ao **Compliance Guiado** via NetBox. Usuário faz upload de arquivo .txt de configuração, seleciona plataforma (Huawei, Cisco, etc), escolhe **Contextos de Analise** e valida contra regras compliance. Sem coleta SSH/SNMP—apenas parser local.

**SNMP Community Hierárquico**:
Resolução de SNMP community em ordem: device.custom_field > tenant.custom_field > env var SNMP_COMMUNITY. Permite override por device sem forçar cada um a ter valor.

## Flagged ambiguities

- "Coleta" foi usado para significar tanto analise guiada imediata quanto pipeline de **Job de Compliance**; resolvido: **Coleta Read-only** e a obtencao de evidencia, enquanto **Compliance Guiado** e **Job de Compliance** sao fluxos que podem aciona-la.
- "Layout" nao deve alterar contratos de API nem fontes de evidencia; ajustes visuais devem preservar os endpoints usados por cada fluxo.
- Compliance pode rodar contra dados do NetBox (**Compliance Guiado**) ou contra arquivo local (**Análise Avulsa**); ambos usam mesmo motor de validação e mesmos **Contextos de Analise**.
