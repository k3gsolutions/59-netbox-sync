# Real Week 1 Activation Flow

## Objetivo
Ativar a coleta real de respostas da Semana 1 pela Web UI, sem CSV manual como fluxo principal.

## Fluxo
1. Abrir `/service-engagement/4WNET-MNS-KTG-RX`.
2. Ver as pendências.
3. Clicar em `Editar pendência`.
4. Preencher os campos.
5. Clicar em `Salvar e fechar`.
6. Ver o status atualizar.
7. Abrir o painel de validação.
8. Clicar em `Finalizar respostas e preparar Semana 2`.
9. Revisar o critério de liberação.
10. Seguir para revisão humana da Semana 2.

## O que não acontece
- Não escreve no NetBox.
- Não aplica configuração.
- Não cria ApplyPlan automaticamente.
- Não aprova nada automaticamente.
- Não trata UAT como real sem decisão explícita.

## Resultado esperado
- Respostas salvas localmente.
- CSV local atualizado.
- Auditoria local criada.
- Validação local atualizada.
- Semana 2 preparada para revisão humana quando o conjunto estiver completo.

## Artefatos locais
- `reports/pilot-device-compliance/REAL-WEEK1-EXECUTION-LOG.md`
- `reports/pilot-device-compliance/REAL-WEEK1-FINAL-VALIDATION.md`
- `reports/pilot-device-compliance/week2-activation-gate.md`

## Multi-cycle follow-up

- Once Week 1 is real, the controlled-operation index tracks cycle state and the Cycle-002 gate.
