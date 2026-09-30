# Plano: TOM determinístico, incremental e comparável ao TypeCompact

Status: planejado; este documento não implementa nem executa os experimentos.

## Objetivo

Testar classificação determinística por chunks durante a sessão, memória tipada persistente e projeção posterior com orçamento. Buscar melhor fronteira entre preservação, tokens, armazenamento e latência bloqueante — não garantir uma vitória sobre TypeCompact.

Hipóteses separadas:

1. Remover overhead e aproveitar melhor o orçamento melhora preservação.
2. Persistir classificação evita trabalho e degradação por reclassificação.
3. Observar durante a sessão reduz a pausa na compactação, sem esconder custo total.

## Diagnóstico de partida

- `TypedTOMMemory.ingest()` armazena eventos pendentes; `compact()` dispara observação. Hoje não há observação em background nesse caminho.
- O runner recria TOM a partir do texto renderizado a cada round. TypeCompact mantém seu KB tipado, mesmo quando o texto pontuado foi truncado.
- `Renderer` insere títulos e IDs. Uma medição dos 20 configs encontrou 33% de overhead em tokens com IDs curtos, antes dos prefixos do adapter.
- `ContextProjector` obriga apenas EXACT; HIGH_FIDELITY entra quando cabe. Comentários do adapter que afirmam proteção incondicional de ambos estão incorretos.
- TOM seleciona com tiktoken e o runner corta por caracteres. Isso pode cortar conteúdo já selecionado como protegido.
- Os resultados existentes são diagnósticos. O upstream inspecionado também usa classificação por cascade/LLM na estabilidade; a variante regex local não é reprodução exata dessa configuração.

## Regras do trabalho

- Reutilizar observer, chunker, store, projector e métricas existentes. Sem novo framework, serviço ou dependência.
- Nenhum benchmark LLM nesta sequência inicial. Permitir selecionar apenas TypeCompact e TOM determinístico sem iniciar bridges.
- Não sobrescrever resultados existentes nem alterar silenciosamente protocolo upstream.
- Conservar texto e proveniência dos itens protegidos. Não resolver orçamento impossível cortando constraints silenciosamente.
- Cada mudança de comportamento deve ter um teste executável; usar a suíte pytest já existente.

## Etapa 1 — Congelar controles e separar protocolos

Arquivo principal: `src/tom/benchmarks/knowledge_triage_repro.py`.

### Entregas

- Manter um modo de compatibilidade upstream, com heurística de caracteres, regras de estado e divergências documentadas. Não misturar seus números com o protocolo controlado.
- Criar duas avaliações controladas:
  - **Texto recursivo:** ambos recebem somente o texto realmente emitido no round anterior; nenhum recupera itens ocultos.
  - **Estado persistente:** ambos mantêm estado tipado e recebem os mesmos eventos incrementais; contexto não substitui o estado. Contabilizar todo armazenamento, inclusive eventos retidos.
- No protocolo controlado, usar o mesmo contador e orçamento para ambos. Isolar no adapter a adaptação do contador do TypeCompact, sem modificar a dependência instalada. Validar o tamanho final com esse contador.
- Usar sequência de orçamentos comum, derivada da entrada original, não do tamanho variável da saída de cada estratégia. Separar um cenário de orçamento fixo com novos chunks de outro de redução progressiva.
- Congelar manifestos: hashes do corpus/configs, splits, ordem dos chunks, budgets, seed, versão do código/dependência, classifier, renderer e políticas.
- Tratar os 20 configs já inspecionados como desenvolvimento. Escolher avaliação ainda não utilizada, separando por repositório/família quando a proveniência permitir e verificando duplicatas. Documentar limites da proveniência disponível.
- Salvar registros por config/round incrementalmente e permitir resume com validação do manifesto. Reutilizar convenções do harness existente.

### Aceite

Teste de contrato prova igualdade de entradas/orçamentos e ausência de estado oculto no modo texto; resume incompatível é rejeitado; execução determinística não cria bridge nem faz chamada LLM.

## Etapa 2 — Manter memória tipada entre compactações

Arquivos principais: `src/tom/benchmarks/typed_strategy.py`, `src/tom/benchmarks/knowledge_triage_repro.py`; store somente se necessário.

### Entregas

- No braço persistente, criar uma instância por histórico e mantê-la durante todos os rounds.
- Observar somente eventos novos. Não reingerir títulos, IDs ou contexto renderizado como fonte.
- Identificar eventos/memórias por sessão e sequência estáveis; suportar ingestões repetidas sem colisões ou duplicações.
- Tornar o armazenamento a fonte recuperável de estado e reusar a materialização existente; evitar duas cópias sem regra clara de sincronização.
- Confirmar persistência antes de considerar um lote processado; falha de observação/gravação não pode perder eventos pendentes.
- Oferecer ao TypeCompact o mesmo acesso a estado persistente e novos chunks. Classificar somente entradas novas também no controle.

### Aceite

Teste com duas ingestões e várias projeções: cada evento é classificado uma vez, fontes permanecem válidas, reinício recupera o estado, e falha/retry não perde nem duplica itens.

## Etapa 3 — Observação incremental em background

Arquivos principais: `src/tom/benchmarks/typed_strategy.py`, `src/tom/observer/deterministic_observer.py`; reutilizar `EventChunker`.

### Entregas

- Usar primitivas da stdlib: fila limitada e um consumidor por sessão ativa, com backpressure explícito.
- Agendar chunks completos na ingestão. Processar o residual em flush/compactação/encerramento.
- Definir uma barreira: compactação espera os eventos aceitos até aquele ponto, não um fluxo infinito de eventos posteriores.
- Não bloquear o event loop com classificação síncrona longa: executar por chunk em thread se necessário; manter gravações no contexto apropriado do store.
- Tornar visíveis erros do worker; finalizar tarefas e conexões sem abandonar lotes. Não criar processamento concorrente do mesmo observer mutável.
- Medir espera na ingestão, fila pendente, tempo de observação, espera na barreira, projeção e tempo total.
- Comparar observação síncrona e background com os mesmos chunks e cadência. Incluir cenário sem tempo ocioso; não simular uma vantagem com pausas artificiais não declaradas.

### Aceite

Teste sincronizado por eventos, sem sleeps frágeis: observação começa antes de compactar; compactação aguarda seu lote; há backpressure; erros chegam ao caller; shutdown drena ou registra explicitamente trabalho não concluído.

## Etapa 4 — Reduzir overhead de contexto

Arquivos principais: `src/tom/context/renderer.py`, `src/tom/context/projector.py`.

### Entregas

- Adicionar renderização compacta usando o ponto de injeção existente do projector, sem substituir o formato legível globalmente.
- Emitir conteúdo sem IDs longos e espaçamento excessivo; manter IDs/proveniência em metadados fora do prompt.
- Contar exatamente a representação emitida. Registrar tokens de conteúdo e de formatação separadamente.
- Aplicar formato equivalente ao controle quando a comparação quiser isolar seleção, e manter uma ablação específica de formato.

### Aceite

Teste garante texto-fonte intacto, fontes recuperáveis e menor overhead. Medir preservação por config, não assumir que tokens economizados se transformam automaticamente em ganho.

## Etapa 5 — Proteção, deduplicação e orçamento impossível

Arquivos principais: `src/tom/context/projector.py`, `src/tom/context/budget.py` e adapter do benchmark.

### Entregas

- Explicitar a política paper-style: constraints e procedimentos protegidos, com orçamento mínimo calculado sobre a representação final.
- Preservar o contrato padrão do projector; introduzir a política comparativa sem alterar silenciosamente outros callers.
- Deduplicar apenas conteúdo idêntico com tipo, escopo e semântica de retenção compatíveis; unir proveniência. Reutilizar consolidação existente se atender a isso.
- Se o mínimo protegido exceder o orçamento, retornar/propagar estado unsafe com tokens necessários.
- Separar resultado estritamente orçado de diagnóstico best-effort acima do orçamento; não apresentar este último como vitória em orçamento igual.
- Remover truncamento externo destrutivo do protocolo controlado. Manter o truncamento apenas no modo de compatibilidade, explicitamente rotulado.

### Aceite

Testes cobrem limite exato, orçamento insuficiente, procedimento longo, duplicatas com fontes diferentes e escopos incompatíveis. Nenhum resultado considerado válido ultrapassa o orçamento ou corta silenciosamente itens protegidos.

## Etapa 6 — Melhorar seleção somente após corrigir o controle

Arquivos principais: `src/tom/context/projector.py` e benchmark.

### Entregas

Comparar, uma alteração por vez, após alocar os itens protegidos:

1. Seleção gulosa atual, como controle.
2. Alocação do TypeCompact, para localizar a diferença de mecanismo.
3. Cobertura mínima dos tipos presentes, seguida de redistribuição de espaço não usado por prioridade e custo.

- Não codificar funções de preservação do avaliador no seletor.
- Não usar deduplicação semântica ou novo LLM nesta fase.
- Ajustar somente em desenvolvimento e congelar a política antes da avaliação.
- Se a política nova não melhorar a fronteira qualidade-consumo, removê-la e registrar o resultado negativo.

### Aceite

Teste de estabilidade, orçamento e redistribuição. Comparação pareada mostra quais tipos ganham/perdem; melhora de macro não pode esconder regressão em constraints/procedimentos.

## Etapa 7 — Avaliação e relatório

### Sequência

1. Testes locais e smoke determinístico de 3 configs.
2. Desenvolvimento nos configs já usados, orçamentos de 50%, 25% e 10%, rounds 1–5.
3. Congelar implementação, manifestos e métricas.
4. Avaliar configs reservados, com as mesmas condições nos dois braços.
5. Repetir medições de desempenho; variar ordem de execução e informar hardware. Repetir exatamente a mesma classificação determinística não cria novas amostras científicas.

### Comparações mínimas

- TypeCompact versus TOM sob o mesmo contrato de estado e orçamento.
- TOM síncrono versus background, mesma política de qualidade.
- Renderer original versus compacto.
- Seleção atual versus proteção/deduplicação versus candidata de alocação.

Executar ablações progressivamente, sem produto cartesiano desnecessário.

### Métricas

- Preservação por tipo, macro, constraint recall por round e pares de casos.
- Tokens reais emitidos, overhead, mínimo protegido e frequência de unsafe.
- Latência bloqueante p50/p95, custo total, CPU, throughput e espera na fila.
- Bytes de eventos/estado/metadados e pico de memória; mesma contabilização nos braços.
- Itens/chunks classificados e reclassificados; chamadas LLM devem ser zero.
- Falhas separadas de qualidade; denominador por round e comparação pareada nos casos comuns. Não excluir unsafe silenciosamente.
- Intervalos pareados por config, agrupados por repositório quando identificável; explicitar limitações da amostra.

### Aceite final

Publicar protocolo, manifestos, comando reproduzível, registros brutos, tabela de ablações e fronteira qualidade-consumo. Concluir mesmo se TypeCompact continuar melhor. Alegar vantagem somente na métrica e no cenário sustentados pelos dados; não chamar redução de latência bloqueante de redução de trabalho total.

## Ordem, esforço e limites

Ordem sugerida: 1 → 2 → 3 → 4 → 5 → 6 → 7. A etapa 4 pode ser preparada após a etapa 1, mas deve ser medida isoladamente.

Estimativa inicial, sujeita aos testes: 1–2 dias para protocolo/harness; 2–3 dias para estado e background; 1–2 dias para renderer/proteção/seleção; 1–2 dias para avaliação e relatório. Total aproximado: 5–9 dias de trabalho, sem garantia de prazo.

Recursos: ambiente Python e dependências atuais, corpus AAC local e CPU; nenhum gasto LLM planejado. Reincluir braços LLM e ampliar para outros benchmarks somente após validar este protocolo.

Riscos principais: concorrência e perda de lotes (barreiras e persistência antes do ack); vantagem aparente por memória externa (contabilização simétrica); overfitting no AAC (holdout); orçamento insuficiente (unsafe explícito); baseline incremental igualmente rápida (resultado negativo legítimo).
