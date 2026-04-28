# Prompt — Pilot Device Compliance

## Objetivo
Analisar um único dispositivo piloto em modo read-only, comparando NetBoxInventory e DeviceInventory com foco em divergências de service_type, tenant, VRF, VLAN/QinQ, IP, BGP e políticas.

## Referências obrigatórias
- `NetBoxInventory`
- `DeviceInventory`
- `docs/14-device-config-discovery-standard.md`
- `docs/15-service-type-dependency-matrix.md`
- `docs/18-compliance-divergence-catalog.md`
- `reports/pilot-device-compliance/TEMPLATE-device-compliance-report.md`

## Instruções
1. Use apenas um dispositivo piloto.
2. Não execute nenhum comando de escrita no NetBox.
3. Não execute nenhum comando de configuração no equipamento.
4. Não rode em lote.
5. Sempre peça confirmação antes de qualquer chamada real à API NetBox.
6. Sempre peça confirmação antes de qualquer leitura real do equipamento.

## Fluxo sugerido
- Revisar o inventário NetBox do dispositivo.
- Revisar o inventário do equipamento.
- Mapear objetos entre NetBox e equipamento.
- Identificar divergências usando os códigos do catálogo.
- Preencher o template de relatório com os resultados.

## Saída esperada
- Relatório Markdown completo com seções de resumo executivo, comparação NetBox x equipamento, divergências e ações recomendadas.
- Uso consistente dos códigos de divergência do catálogo.
- Recomendação clara de correções no NetBox e/ou no equipamento.

## Observação
Este prompt serve apenas para orientação de análise e geração de relatório; não deve ser usado para implementar mudanças automáticas.
