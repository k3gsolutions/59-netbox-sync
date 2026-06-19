---
name: ship-loop
description: Execute ciclos autônomos controlados de desenvolvimento com leitura, plano, edição, testes, validação e relatório final. Use para implementar features, corrigir bugs, revisar codebase, criar testes, validar frontend/backend e atualizar contexto operacional sem ações destrutivas.
---

# Ship Loop

Use esta skill quando o usuário pedir para:

- analisar codebase
- implementar feature
- corrigir bug
- criar endpoint
- ajustar frontend
- escrever testes
- validar fluxo
- executar ciclo read/write/test/validate
- atualizar TODO.md, CONTEXT.md ou documentação operacional

## Objetivo

Operar o PI como agente autônomo controlado dentro de um codebase, seguindo o ciclo:

```text
READ → PLAN → EDIT → TEST → VALIDATE → REPORT
```

A skill deve evitar execução impulsiva, reduzir risco operacional e garantir que toda alteração seja pequena, rastreável e validada.

## Política de segurança

- Read-only por padrão.
- Nunca use sudo.
- Nunca instale pacotes sem aprovação explícita.
- Nunca apague arquivos sem aprovação explícita.
- Nunca execute comandos destrutivos.
- Nunca altere `.env` real.
- Nunca exponha secrets, tokens, senhas ou chaves.
- Nunca faça writes externos em NetBox, APIs reais, bancos reais ou equipamentos de rede sem aprovação explícita.
- Antes de editar, leia o arquivo.
- Depois de editar, execute validação.
- Se a validação falhar, diagnostique antes de alterar novamente.
- Não simule tool calls.
- Não escreva JSON de tool em markdown.
- Use tools reais do PI.

## Ações permitidas sem aprovação

Pode executar sem perguntar:

```bash
pwd
ls
find
grep
cat
git status
git diff
python -m py_compile
pytest -q
npm test
npm run lint
npm run build
```

Use bom senso: se um comando seguro puder gerar saída enorme, limite com `head`, `tail`, filtros ou escopo específico.

## Ações que exigem aprovação explícita

Peça aprovação antes de executar:

```bash
sudo
rm
rm -rf
mv em massa
chmod/chown recursivo
git reset
git clean
git push
docker compose down -v
pip install
npm install
apt install
alembic upgrade
migrations destrutivas
curl POST/PUT/PATCH/DELETE para produção
comandos em roteadores reais
writes em NetBox/API real
alteração de banco real
```

Se houver dúvida se uma ação é destrutiva, pare e peça aprovação.

## Diretórios ignorados

Ignore por padrão:

- `.git`
- `.venv`
- `venv`
- `node_modules`
- `__pycache__`
- `.pytest_cache`
- `dist`
- `build`
- `data`
- `logs`
- arquivos binários
- bancos locais, exceto se o usuário pedir explicitamente

## Loop obrigatório

Execute sempre em ciclos pequenos.

```text
READ → PLAN → EDIT → TEST → VALIDATE → REPORT
```

Não tente resolver muitas coisas ao mesmo tempo. Prefira uma alteração pequena e validada por ciclo.

## Fase 1 — READ

Objetivo: entender o estado atual antes de qualquer alteração.

Ações recomendadas:

1. Confirmar diretório atual.
2. Verificar status do Git.
3. Mapear arquivos relevantes.
4. Ler arquivos antes de editar.
5. Identificar entrypoints, configs e testes existentes.

Comandos seguros:

```bash
pwd
git status --short
find . -maxdepth 3 \
  -path './.git' -prune -o \
  -path './.venv' -prune -o \
  -path './venv' -prune -o \
  -path './node_modules' -prune -o \
  -path './__pycache__' -prune -o \
  -path './.pytest_cache' -prune -o \
  -path './data' -prune -o \
  -type f -print | sort | head -200
```

Arquivos de alto valor para ler, se existirem:

- `README.md`
- `AGENTS.md`
- `CONTEXT.md`
- `TODO.md`
- `CHANGELOG.md`
- `pyproject.toml`
- `package.json`
- `docker-compose.yml`
- `Dockerfile`
- `Makefile`
- `.env.example`
- arquivos de entrypoint da aplicação
- arquivos diretamente relacionados à tarefa

## Fase 2 — PLAN

Antes de editar, apresente um plano curto.

Formato obrigatório:

```text
[OBJETIVO]
Descrever a tarefa em uma frase.

[ARQUIVOS-ALVO]
Listar arquivos que serão lidos ou alterados.

[ALTERAÇÃO]
Descrever a mudança mínima planejada.

[VALIDAÇÃO]
Descrever quais testes/comandos serão executados.

[RISCO]
Baixo/Médio/Alto e motivo.
```

Não altere arquivos antes de ter clareza do plano.

## Fase 3 — EDIT

Objetivo: fazer a menor alteração possível que resolva a tarefa.

Regras:

- Alterar somente o necessário.
- Preservar estilo existente.
- Evitar reescrever arquivo inteiro sem necessidade.
- Preferir mudanças pequenas e verificáveis.
- No máximo 3 arquivos por ciclo, salvo instrução contrária.
- Não misturar refatoração grande com correção pequena.
- Não alterar comportamento fora do escopo da tarefa.

Antes de editar:

1. Ler o arquivo-alvo.
2. Identificar o trecho exato.
3. Aplicar alteração mínima.
4. Conferir diff.

Depois de editar:

```bash
git diff -- <arquivo>
```

## Fase 4 — TEST

Objetivo: validar que a alteração não quebrou o projeto.

Validação Python:

```bash
python -m py_compile <arquivo>
pytest -q
```

Validação frontend, se houver `package.json`:

```bash
npm test
npm run lint
npm run build
```

Validação FastAPI, se aplicável:

```bash
python -m uvicorn app.main:app --reload
```

ou use o entrypoint real detectado no projeto.

Validação shell, se aplicável:

```bash
bash -n <script.sh>
```

Se não existir teste automatizado, faça validação mínima por import, lint sintático ou execução controlada read-only.

## Fase 5 — VALIDATE

Objetivo: interpretar o resultado dos testes.

Se passar:

- registrar evidência
- atualizar TODO/CONTEXT se necessário
- reportar conclusão

Se falhar:

1. Ler erro com atenção.
2. Identificar causa provável.
3. Fazer no máximo 2 tentativas de correção.
4. Rodar teste novamente.
5. Se continuar falhando, parar e reportar.

Nunca esconda erro de teste. Nunca declare sucesso sem evidência.

## Fase 6 — REPORT

Ao final de cada ciclo, responder neste formato:

```text
[OBJETIVO]
...

[STATUS]
Concluído / Parcial / Bloqueado

[ARQUIVOS LIDOS]
...

[ARQUIVOS ALTERADOS]
...

[TESTES EXECUTADOS]
...

[RESULTADO]
...

[PENDÊNCIAS]
...

[PRÓXIMA AÇÃO]
...
```

## Atualização de contexto

Atualize `TODO.md`, `CONTEXT.md` ou documentação operacional quando:

- a tarefa mudou o fluxo do projeto
- uma decisão técnica foi tomada
- um bug importante foi descoberto
- uma pendência nova apareceu
- uma feature foi concluída
- houver informação útil para continuidade em outro chat/agente

Não atualize contexto com ruído ou detalhes temporários irrelevantes.

## Critérios de parada

Pare imediatamente se encontrar:

- necessidade de comando destrutivo
- necessidade de instalar pacote
- necessidade de mexer em produção
- necessidade de alterar banco real
- necessidade de executar write em NetBox/API real
- necessidade de comando em roteador real
- falha de teste persistente após 2 tentativas
- ambiguidade que possa causar perda de dados ou alteração fora de escopo

## Modo para análise de codebase

Quando a tarefa for apenas analisar o projeto:

1. Não editar arquivos.
2. Mapear estrutura.
3. Ler arquivos de alto valor.
4. Identificar stack, arquitetura e fluxo.
5. Entregar síntese operacional.

Formato de saída:

```text
[OBJETIVO DO PROJETO]
...

[STACK]
...

[ARQUITETURA]
...

[FLUXO DE EXECUÇÃO]
...

[MÓDULOS PRINCIPAIS]
...

[COMO SUBIR LOCALMENTE]
...

[RISCOS/PENDÊNCIAS]
...

[PRÓXIMOS PASSOS]
...
```

## Modo para implementação

Quando a tarefa for implementar algo:

1. Ler contexto.
2. Planejar alteração mínima.
3. Editar.
4. Testar.
5. Validar.
6. Reportar.

Não implementar múltiplas features em uma rodada.

## Modo para correção de bug

Quando a tarefa for corrigir bug:

1. Reproduzir ou localizar evidência do erro.
2. Identificar causa provável.
3. Alterar o mínimo.
4. Rodar teste.
5. Validar se o erro foi corrigido.
6. Verificar se não quebrou comportamento relacionado.

## Modo para frontend

Quando a tarefa envolver frontend:

- preservar identidade visual existente
- reduzir ruído visual
- priorizar UX clara
- manter linguagem amigável ao usuário final
- evitar excesso de logs técnicos na tela
- preservar responsividade
- validar HTML/CSS/JS quando possível

## Modo para NetOps/NetBox

Quando a tarefa envolver NetBox, SNMP, roteadores ou compliance de rede:

- coleta read-only por padrão
- SNMP apenas leitura
- SSH apenas diagnóstico sem alteração, salvo aprovação
- writes em NetBox exigem aprovação
- comandos em roteadores reais exigem aprovação
- sempre separar diagnóstico de ação corretiva
- gerar comandos de correção apenas como proposta, não executar sem aprovação

## Frases proibidas

Evite:

- “vou executar” sem executar
- “parece que funcionou” sem evidência
- “provavelmente está certo” sem validação
- JSON de tool em markdown
- simulação de tool call

## Frases preferidas

Use:

- “Executei...”
- “Validei com...”
- “Falhou em...”
- “Bloqueado porque...”
- “Alteração feita em...”
- “Próxima ação recomendada...”
