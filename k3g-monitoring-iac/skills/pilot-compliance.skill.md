# Skill — Pilot Compliance

## Objetivo
Planejar, revisar e orientar a execução de um piloto de compliance de um único dispositivo, comparando inventário NetBox e inventário do equipamento sem aplicar qualquer mudança.

## Quando usar
- Ao preparar o primeiro piloto controlado de compliance.
- Ao documentar divergências entre NetBox e dispositivo.
- Ao validar readiness do NetBox antes de iniciar automação.

## Entrada esperada
- NetBoxInventory do dispositivo piloto.
- DeviceInventory coletado do equipamento.
- Matriz de dependências de service_type.
- Catálogo de divergência.
- Template de relatório de compliance.

## Saída esperada
- Relatório de compliance preenchido.
- Lista de divergências categorizadas e priorizadas.
- Recomendações de correção no NetBox e no equipamento.
- Checklist de execução de piloto.

## Checklist
- [ ] Piloto limitado a um único dispositivo.
- [ ] Coleta apenas read-only.
- [ ] Não houve escrita no NetBox.
- [ ] Não houve escrita no equipamento.
- [ ] Uso do catálogo de divergências para classificar gaps.
- [ ] Preenchimento do relatório em Markdown.
- [ ] Riscos e rollback documentados.

## Anti-padrões
- Tentar automatizar correções durante o piloto.
- Rodar verificação em lote ou em vários dispositivos.
- Usar dados incompletos do NetBox para tirar conclusões.
- Ignorar desvios críticos de metadata ou naming.
