# Skill — NetBox Modeling

## Objetivo
Modelar dados no NetBox garantindo aderência à automação e ao GitOps.

## Quando usar
- Criar/atualizar sites, tenants, devices, interfaces, circuits.
- Introduzir novos custom fields.
- Ajustar naming conventions.

## Entrada esperada
- Requisitos de modelagem.
- Dados atuais e gaps.
- Custom fields necessários.

## Saída esperada
- Plano de modelagem.
- Lista de campos obrigatórios.
- Implicações em workflows/templating.
- Ações de saneamento.

## Checklist
- [ ] Custom fields definidos e versionados?
- [ ] Naming convention aplicada?
- [ ] Tags coerentes com taxonomia?
- [ ] Tenants/tenant groups mapeados?
- [ ] Integração com BGP plugin?
- [ ] Campos obrigatórios validados?
- [ ] Documentação atualizada?

## Anti-padrões
- Alterar dados sem refletir em Git.
- Criar campos duplicados.
- Usar NetBox como datastore informal.
- Depender de descrição humana sem padrões.