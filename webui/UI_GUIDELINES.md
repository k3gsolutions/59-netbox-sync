# NetOps WebUI — Padrões de Design e UX

Este documento descreve o padrão arquitetural e visual estabelecido para as interfaces frontend do projeto **NetOps NetBox Sync**, com foco especial no fluxo de **Compliance Guiado**. Agentes de IA e desenvolvedores devem seguir estritamente estas diretrizes ao adicionar ou modificar telas.

## 1. Identidade Visual e Layout

O layout segue o estilo **Dark Theme Premium**, otimizado para profissionais de redes que passam longos períodos diante de telas.

### 1.1. Cores e Tipografia (Design Tokens)
- **Background Principal:** `#121212`
- **Superfícies/Cards:** `#1A1A1A` ou `#1E1E1E` (leve elevação)
- **Bordas e Linhas:** `#333333`
- **Cores Semânticas:**
  - Sucesso/Aprovado: `#10B981` (texto/borda) e `#064E3B` (fundo atenuado)
  - Atenção/Warning: `#F59E0B` (texto/borda) e `#78350F` (fundo atenuado)
  - Erro/Reprovado: `#EF4444` (texto/borda) e `#7F1D1D` (fundo atenuado)
- **Tipografia:** 
  - Fonte padrão: `Inter`, sans-serif
  - Fonte para itens técnicos (IPs, variáveis, evidências): `JetBrains Mono` ou monospace.

### 1.2. Estrutura da Página
As interfaces seguem o modelo de Dashboard Clássico:
- **Sidebar (Esquerda):** Menu fixo de navegação, com logo superior e *status dot* da API no rodapé.
- **Header:** Área no topo contendo título da tela, subtítulo e botões de configuração global (ex: URL/Token da API).
- **Conteúdo Central (`.app-main`):** Container principal responsivo onde os *Wizards* ou *Relatórios* são renderizados.

## 2. Padrão de "Wizard" (Fluxo em Cascata)

A tela de Compliance (`compliance.html`) segue o padrão de **Wizard Interativo**. Ele é projetado para evitar sobrecarga cognitiva.

### Regras de Ouro do Wizard:
1. **Exibição Progressiva:** Apenas o passo atual e os já concluídos devem ser visíveis ou interagíveis. Passos futuros devem estar ocultos.
2. **Indicador de Progresso (Stepper):** No topo, os círculos numerados indicam os passos. Se um passo já foi feito (`.done` ou `.active`), o indicador **deve permitir o clique** para que o usuário possa retornar sem perder o progresso.
3. **Botão Voltar:** Além dos indicadores de passos clicáveis no topo, cada etapa avançada (Passos 2, 3 e 4) deve sempre possuir um botão **"← Voltar"** para o passo imediatamente anterior.
4. **Preservação de Estado:** Ao voltar um passo, os itens selecionados (ex: Cliente ativo ou Contextos marcados) **não devem ser apagados**. O sistema só recarrega a próxima etapa se a seleção for alterada.

## 3. Feedback Visual e Interação

- **Hover Effects:** Elementos interativos (cards, botões, ícones de steps) **devem** ter feedback visual no mouse (ex: `transform: translateY(-2px)`, mudança de cor nas bordas, e `cursor: pointer`).
- **Loading States:** Requisições à API devem sempre ocultar a lista anterior e mostrar um `div.loading-row` contendo um spinner animado e texto indicativo (ex: "Carregando dispositivos...").
- **Error States:** Se uma API falhar, um box avermelhado `.error-row` deve ser exibido com clareza, explicando o motivo (ex: falha de timeout, ausência de credencial).
- **Cards Selecionáveis (`.card.selected`):** Itens escolhidos no fluxo recebem borda com cor de destaque (ex: `#3B82F6` ou verde) e leve resplendor (`box-shadow`), sinalizando sua ativação.

## 4. Estado da Aplicação e Vanilla JS

Não utilizamos frameworks (React/Vue) para esta UI, garantindo máxima leveza e facilidade de deploy de arquivos estáticos pelo FastAPI.

- **Persistência de Configurações:** URL da API e Tokens devem ser salvos no `localStorage` do navegador para evitar digitação a cada F5.
- **Objeto State Global:** O controle de navegação fica em uma variável `state` única:
  ```javascript
  let state = {
    currentStep: 1,
    selectedTenant: null,
    selectedDevice: null,
    selectedContexts: new Set(),
    findings: [],
  };
  ```
- **Navegação (`goToStep`):** Manipula visibilidade via classes (`.hidden`).

## 5. Cuidados Adicionais para Agentes de IA

1. **NÃO REMOVA OU REDUZA** o CSS existente para tentar simplificar. A estética "Premium" é um requisito crítico do projeto.
2. Não utilize `alert()` nativo do navegador; crie Modais customizados para detalhes ou erros grandes (ex: `detail-modal` do compliance).
3. Respeite as paletas de cores semânticas nos relatórios (não utilize vermelho se for apenas um aviso).
4. Em tabelas ou listas, exiba dados técnicos SEMPRE dentro de blocos `.mono` ou usando fontes monospace.
