# Skill — N8N Workflow

## Objetivo
Planejar, revisar e validar workflows N8N alinhados aos princípios do projeto.

## Quando usar
- Ao criar novo workflow.
- Ao revisar alteração de workflow existente.
- Antes de mover workflow para produção.

## Entrada esperada
- Objetivo do workflow.
- Trigger, inputs e outputs.
- Dependências e integrações.
- Dados de configuração (variáveis, credenciais).
- Estado atual do NetBox/N8N.

## Saída esperada
- Descrição passo a passo.
- Verificação de idempotência.
- Estratégia de dry-run e audit log.
- Plano de testes (smoke e regressão).
- Riscos e mitigação.

## Checklist
- [ ] Trigger definido e seguro?
- [ ] Inputs validados?
- [ ] Idempotência garantida?
- [ ] Dry-run implementado?
- [ ] Audit log registrado?
- [ ] Error handler direciona para DLQ?
- [ ] Variáveis/credenciais seguras?
- [ ] Testes documentados?
- [ ] Documentação atualizada?

## Anti-padrões
- Workflow sem controle de estado.
- Uso de credenciais hardcoded.
- Falta de rollback.
- Ignorar DLQ ou alertas de falha.