# Plano de correção da comparação TOM × TypeCompact

## Objetivo

Separar perdas causadas pelo protocolo, pelo formato do prompt e pela seleção de memórias. Não pressupor que TOM vencerá. Primeiro validar controles determinísticos; depois repetir os braços Codex, sem apagar resultados anteriores.

Este plano complementa `tom-deterministic-improvement-plan.md`: reutilizar os protocolos, manifestos, renderer, projector e testes já existentes. Não reimplementar etapas já entregues nem criar outro framework.

## Diagnóstico que motiva o plano

- O runner legado usa `truncate_to_tokens`, que corta caracteres (4 caracteres/token), enquanto TOM usa tokenizer no projector.
- No legado multi-round, TypeCompact mantém `compacted_kb`, mas TOM recebe somente texto já cortado. Os próximos budgets também dependem de representações diferentes.
- O braço legado TOM usa renderer original e seleção padrão; portanto não mede automaticamente as melhorias opcionais já implementadas.
- Mesmo o runner controlado deriva budgets de `kb.total_tokens` e chama TypeCompact com estimativas próprias. Medir a saída com tiktoken não equivale a selecionar com o mesmo contador.
- O modo texto controlado pode alimentar a próxima rodada com diagnóstico acima do orçamento e registrar TOM como `ok`.
- O relatório de estado persistente deve pontuar somente fatos já recebidos, não fatos de rodadas futuras.
- `SelectionPolicy.TYPE_COMPACT` aproxima quotas, mas não reproduz exatamente a seleção upstream.
- O split 80/20 anterior foi feito depois da execução. Não é um holdout intocado. O bootstrap anterior reamostra rodadas dependentes como se fossem observações independentes.

## Regras comuns

1. Preservar resultados existentes como exploratórios/legados; nunca sobrescrevê-los.
2. Manter modo de compatibilidade upstream separado e explicitamente rotulado. Não alterar silenciosamente seus números ou defaults.
3. Nenhum benchmark LLM antes dos testes de contrato e do congelamento da avaliação corrigida.
4. Usar pytest e dependências existentes. Registrar falhas e unsafe; não descartá-los nem convertê-los em texto vazio com score zero sem distinção.
5. O objetivo é uma comparação justa, não otimizar no conjunto final até TOM vencer.

## Etapa 1 — Fixar contratos dos protocolos

Arquivos: `src/tom/benchmarks/knowledge_triage_repro.py`, `tests/unit/test_knowledge_triage_repro.py`.

### Entregas

- Identificar explicitamente `upstream_compat` e uma nova versão do protocolo controlado no manifesto e relatório.
- Texto recursivo: ambos começam com o mesmo texto; cada braço recebe apenas sua própria saída válida na rodada seguinte, sem estado estruturado oculto. As entradas podem divergir depois da primeira rodada por definição.
- Estado persistente: ambos recebem os mesmos eventos incrementais; ambos retêm o histórico estruturado aceito e projetam sob orçamento. Não confundir esse teste com recompactação destrutiva.
- Derivar todos os budgets de `count_tokens(original_text)` e de uma agenda fixa/progressiva comum. Registrar piso de 64 tokens explicitamente.
- Registrar IDs/hash dos eventos aceitos, fontes disponíveis, agenda e configuração das políticas.
- Pontuar estado persistente contra o prefixo recebido; no texto recursivo, contra a entrada original.

### Aceite

Testes demonstram igualdade de budgets, igualdade de eventos no modo persistente, ausência de memória oculta no texto e impossibilidade de pontuar conteúdo futuro como perdido.

## Etapa 2 — Unificar orçamento e tratamento de unsafe

Arquivos: runner, `src/tom/context/projector.py`, `src/tom/context/budget.py`, testes correspondentes.

### Entregas

- Usar o mesmo tokenizer e contar a representação final, incluindo separadores e títulos.
- Isolar a adaptação do TypeCompact no adapter: preservar prioridades e regras upstream, substituindo a contabilidade por custos da saída realmente emitida. Validar a equivalência de seleção quando custos coincidirem.
- Identificar o braço adaptado como `TypeCompact_token_aligned`; manter o upstream intacto como referência. Não confundir correção de contagem com nova política de seleção.
- Proibir truncamento externo nos protocolos controlados.
- Propagar resultado estruturado com `status`, `budget`, `output_tokens`, `required_tokens` e diagnóstico separado da saída válida.
- No texto recursivo, unsafe encerra a cadeia daquele braço: rodadas posteriores ficam `not_run_after_unsafe`, não recebem texto acima do limite. Permanecem no relatório de completude.
- No estado persistente, unsafe não apaga estado; novos eventos podem continuar sendo recebidos. Cada projeção registra seu próprio status.
- `comparison_valid` exige sucesso e respeito ao orçamento, não apenas comprimento curto.

### Aceite

Casos de limite exato, Unicode, separadores, procedimento longo, mínimo protegido acima do limite e unsafe recursivo. Nenhum resultado válido excede o orçamento; nenhuma falha desaparece do denominador.

## Etapa 3 — Isolar formato e política de seleção

Arquivos: `src/tom/context/renderer.py`, `src/tom/context/projector.py`, `src/tom/observer/deterministic_observer.py`, testes.

### Entregas

- Reutilizar renderer compacto: IDs e proveniência continuam no estado, fora do prompt.
- Medir custo total emitido e custo do conteúdo isolado; explicar que tokenização não é aditiva. Não apresentar contagens de strings separadas como decomposição exata do total.
- Avaliar renderer original e compacto mantendo a seleção fixa.
- Avaliar proteção padrão versus paper (constraints + procedimentos), sem alterar contratos dos callers padrão.
- Depois comparar greedy, quotas aproximadas e coverage mantendo renderer e proteção fixos. Nomear quotas como aproximação, não paridade upstream.
- Tornar explícito o desempate por recência/ordem. Para paridade, usar a mesma ordem de origem; recência fica como ablação separada se necessária.
- Não retirar títulos automaticamente por regex: podem fazer parte da entrada legítima. Registrar o efeito da reingestão de formatação no modo recursivo.

### Aceite

Testes adversariais com várias beliefs disputando espaço com preferências, procedimentos longos, duplicatas e escopos incompatíveis. Coverage deve ter sua limitação documentada: priorizar tipos não garante que todos caibam.

## Etapa 4 — Diagnóstico por item e registro incremental

Arquivos: runner, `src/tom/benchmarks/stage7.py`, testes.

### Entregas

- Persistir cada configuração/braço/rodada imediatamente, com saída, hashes, políticas, status e métricas por tipo.
- Registrar itens selecionados e excluídos, fontes e motivos observáveis: protegido, duplicado, fora do orçamento ou não selecionado. Não inferir causalidade apenas a partir de médias.
- Para o modo recursivo, rastrear preservação contra itens originais por meio das métricas existentes.
- Validar resume pelo manifesto e identidade do registro. Pular chamadas já concluídas; preservar resultados parciais em timeout.
- Usar diretório novo por execução. Guardar versão upstream, hashes do código/dependências, tokenizer, seed e modelo/provider.

### Aceite

Teste de interrupção/retomada sem duplicação; rejeição de manifesto incompatível; erro do provider registrado sem perder os sucessos anteriores. Testes específicos do sumarizador, que hoje não estão cobertos só porque a suíte geral passa.

## Etapa 5 — Reavaliação determinística e análise estatística

### Ordem

1. Casos sintéticos de contrato.
2. Reexecução diagnóstica nas mesmas 5 configs, rotulada como desenvolvimento.
3. Congelar código, manifesto, métricas primárias e matriz antes de nova avaliação.
4. Usar novos dados não examinados, preferencialmente separados por repositório de origem. Se indisponíveis, reportar a avaliação como exploratória, sem chamar o split pós-hoc de holdout.

### Matriz mínima

- Protocolos: texto recursivo e estado persistente.
- Ratios: 0,50 / 0,25 / 0,10; cinco rodadas; agenda fixada por protocolo.
- Braços: TypeCompact alinhado e TOM determinístico.
- Ablações TOM: renderer primeiro, proteção depois, seleção por último. Evitar produto cartesiano sem hipótese.

### Métricas

- Primárias: recall de constraints e procedimentos por rodada; proporção de projeções seguras e completas.
- Secundárias: preservação por tipo e macro, tokens emitidos, mínimo protegido, latência, tamanho do estado.
- Mostrar resultados de qualidade nos pares válidos, sua cobertura e taxas de falha em todos os casos planejados. Diagnósticos acima do orçamento não contam como vitórias.
- Para intervalos de confiança, agregar rodadas por configuração e reamostrar pares de configurações; se houver dependência por repositório, usar esse agrupamento. Não tratar cinco rodadas como cinco amostras independentes.
- Classificação por regex não é ground truth independente. Registrar essa limitação e prever auditoria de rótulos/avaliação downstream antes de conclusões semânticas gerais.

### Aceite

Relatório Markdown com tabelas, diferenças pareadas, ICs, taxas de unsafe, casos concretos de perda e comandos reproduzíveis. Sem alegação de reprodução completa do paper.

## Etapa 6 — Somente então repetir Codex

- Reutilizar o adapter Codex existente com gravação incremental e resume corrigidos.
- Smoke de uma configuração antes de ampliar. Mesmos protocolos e budgets dos braços determinísticos.
- Registrar modelo real, prompts, uso retornado pelo provider, latência, retries e erros; não estimar tokens de saída por número de palavras como se fossem medidos.
- Separar observador LLM e compactor vanilla, deixando clara a diferença de tarefa.
- Preservar os resultados Codex antigos como comparação legada; não misturar protocolos na mesma média.
- Não lançar tarefas longas sem persistência parcial. Acompanhar completude e quota por lote, sem prometer monitoramento fora da sessão.

## Critério de decisão

- Se alinhar protocolo e renderer fechar a diferença, a principal causa era o adapter, não o conceito de memória tipada.
- Se permanecer perda em preferências/procedimentos, avaliar seleção com os rastros por item.
- Se TypeCompact continuar superior sob controles equivalentes, reportar isso. Avaliar vantagens próprias do TOM (proveniência, recuperação, estado incremental e tarefas downstream) separadamente, sem usá-las para esconder uma derrota em compactação.

## Próxima ação

Implementar somente as Etapas 1 e 2 e seus testes. Executar diagnóstico determinístico antes de mudar políticas ou consumir quota Codex.
