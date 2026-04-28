# 17 — Pilot Device Compliance Plan

## Objetivo do piloto
Avaliar um dispositivo piloto com um comparativo read-only entre o inventário NetBox e o inventário do equipamento, gerando relatório de divergências e recomendações sem aplicar qualquer mudança.

## Como escolher o dispositivo
- Dispositivo com serviço crítico mas de baixo risco operacional.
- Preferência por equipamento com conexão de gerenciamento já validada.
- Dispositivo com pelo menos um serviço de cliente ou transporte mapeado no NetBox.
- Evitar equipamentos em manutenção ou com mudanças recentes.
- Escolher um dispositivo que represente um caso típico de service_type usado no ambiente.

## Pré-requisitos
- Acesso read-only ao NetBox com permissões de consulta para Device, Interface, VRF, BGP e Circuit.
- Acesso operacional read-only ao equipamento piloto para coleta de inventário.
- Inventário NetBox já cadastrado com custom fields mínimos (`service_type`, `tenant`, `netbox_id`, `criticality`).
- Folha de pilotagem com dispositivo identificado e stakeholder de operação informado.
- Ambiente isolado de execução para evitar consultas em lote ou varreduras em massa.

## Dados necessários
- NetBoxInventory do dispositivo: Device, Interfaces, VRFs, VLANs/QinQ, IPs, BGP peers, route-policies, prefix-lists, ASN.
- DeviceInventory do equipamento: configuração de interfaces, descrições, IPs, VRFs, VLANs/QinQ, BGP peers, route-policies, listas de prefixos, AS-path filters, community lists.
- Matriz de dependência de service_type (`docs/15-service-type-dependency-matrix.md`).
- Checklist de readiness NetBox (`docs/16-netbox-readiness-checklist.md`).
- Catálogo de divergência (`docs/18-compliance-divergence-catalog.md`).

## Fluxo de execução
1. Validar o escopo do piloto e solicitar confirmação do dispositivo selecionado.
2. Coletar NetBoxInventory do dispositivo.
3. Coletar DeviceInventory do equipamento de forma read-only.
4. Mapear objetos NetBox e objetos do equipamento segundo naming convention.
5. Identificar divergências usando o catálogo de divergências.
6. Preencher o template de relatório em `reports/pilot-device-compliance/TEMPLATE-device-compliance-report.md`.
7. Revisar e assinar o relatório com o time antes de qualquer ação corretiva.

## Comandos permitidos
- Consultas API ao NetBox para leitura de inventário.
- Comandos de leitura no equipamento (show, display, verify) que não alterem configuração.
- Comandos de extração de configuração textual ou status operacional.
- Comandos de documentação de resultado ou exportação para Markdown.

## Comandos proibidos
- Qualquer comando de configuração (`configure`, `edit`, `set`, `commit`, `write`).
- Comandos que alterem estado do equipamento ou serviço.
- Comandos em lote que coletem inventário de mais de um dispositivo.
- Ações automáticas em NetBox ou no equipamento.
- Scripts que façam escrita direta em NetBox.

## Arquivos esperados de saída
- `reports/pilot-device-compliance/TEMPLATE-device-compliance-report.md` preenchido com o piloto.
- Relatório final Markdown com divergências e recomendações.
- Registro de evidência do inventário NetBox e DeviceInventory coletado.
- Sumário executivo e plano de ações no próprio relatório.

## Critérios de aceite
- O relatório contém comparativo NetBox vs equipamento para o dispositivo piloto.
- Todas as divergências documentadas usam códigos do catálogo de divergência.
- Há recomendação clara de correção no NetBox ou no equipamento.
- Não há ações aplicadas no equipamento ou no NetBox.
- O piloto é limitado a um único dispositivo.

## Riscos
- Falso positivo por inventário incompleto no NetBox.
- Comando de leitura que impacte performance se usado de forma indevida.
- Seleção de dispositivo com serviço crítico demais para um piloto inicial.
- Divergências não diagnosticadas corretamente por falta de metadata.

## Rollback operacional (read-only)
Mesmo sendo read-only, deve haver um plano de recuperação de operação:
- Encerrar imediatamente a sessão de coleta se houver impacto.
- Reverter qualquer ação humana não autorizada caso seja detectada.
- Documentar o tempo e o comando que gerou a coleta.
- Comunicar o time de operações se qualquer anomalia for identificada.
- Validar que nenhum objeto foi alterado no NetBox após a coleta.

## Checklist de execução
- [ ] Dispositivo piloto escolhido e confirmado.
- [ ] Acesso NetBox read-only validado.
- [ ] Acesso equipamento read-only validado.
- [ ] NetBoxInventory coletado.
- [ ] DeviceInventory coletado.
- [ ] Comparativo realizado usando o catálogo de divergências.
- [ ] Relatório preenchido no template.
- [ ] Nenhuma escrita executada em NetBox ou equipamento.
- [ ] Relatório revisado antes da ação corretiva.
