# Próximos passos: validar TOM em benchmarks públicos

## Situação das etapas 1 e 2

A infraestrutura das etapas 1 e 2 foi revisada e está implementada no runner:

- **Etapa 1:** o bridge usa o provider Codex autenticado pelo Pi sem criar sessão de agente, não habilita ferramentas, valida IDs das requisições, aplica timeout/retries controlados, encerra o processo e preserva usage/modelo/stop reason quando fornecidos. O caminho do pacote Node é resolvido em tempo de execução.
- **Etapa 2:** cada execução persiste hash do dataset, configuração, modelo, uso do answerer, eventos normalizados, memórias, contexto, resposta, avaliação e latências por fase. `exact_match` agora é igualdade normalizada; `adversarial_answer` fica como metadado e não altera o gabarito.

Ainda não são consideradas concluídas as etapas 1–2 em sentido científico: falta validar as amostras oficiais e inspecionar os erros dos casos iniciais para classificar ingestão, extração, projeção/recuperação ou resposta. Usage ausente continua registrado como `null`, nunca como custo zero.

## Etapa 3 implementada

O runner agora processa o fluxo online: eventos são persistidos no ledger, divididos em chunks limitados por tokens sem reordenar ou dividir eventos, observados uma única vez por histórico e recuperados de forma orientada pela pergunta. A execução reutiliza o estado do histórico entre perguntas, acumula métricas de ingestão/observação e mantém os itens extraídos e o contexto nos diagnósticos.

## Diagnóstico inicial e limites

Os ensaios existentes são smoke tests: cinco perguntas consecutivas do LoCoMo, da mesma conversa, e uma do LongMemEval. Não permitem concluir que TOM é bom ou ruim, nem comparar com os papers. O 1/5 reportado para LoCoMo foi uma leitura posterior das respostas: os registros originais têm score=null, não uma avaliação oficial. LongMemEval teve uma única resposta incorreta.

Há problemas de implementação e de avaliação que precisam ser separados da hipótese científica:

- O bridge atual chama createAgentSession. Apesar de não executar o CLI, ainda usa a sessão de agente Pi e seu carregamento padrão de recursos. Isso não atende ao isolamento solicitado.
- LoCoMo perdeu identificação de falantes no conteúdo enviado às baselines; datas em formatos não ISO viram 1970 silenciosamente. A data da pergunta LongMemEval não é enviada ao answerer.
- O TOM atual observa todo o histórico em uma chamada e refaz a observação para cada pergunta, inclusive quando o histórico é igual.
- Não foram persistidos os itens extraídos nem o contexto final, impedindo localizar exatamente onde um fato se perdeu.
- OM e Knowledge Triage são heurísticas locais, não implementações dos trabalhos originais.
- O scorer chamado exact_match também aceita substring; ausência de métricas é registrada como zero e os tokens de saída do bridge são contados como palavras. Não são métricas publicáveis.

## 1. Corrigir a infraestrutura antes de otimizar TOM

### Entregas

- Substituir createAgentSession por chamada de inferência direta ao provider Codex, reutilizando apenas autenticação OAuth, renovação e transporte. Sem ferramentas, extensões, skills, prompts de agente ou compactação automática.
- Resolver a dependência Node sem caminho absoluto de instalação; registrar versão e modelo efetivamente utilizados.
- Adicionar timeout, fechamento do processo, validação de IDs de requisição e propagação explícita de erros/refusal/truncamento. Não salvar credenciais no repositório ou resultados.
- Registrar usage real quando disponível; usar null e indicar estimativa quando não disponível. Consumo da assinatura não equivale a custo monetário zero.
- Validar formatos oficiais dos datasets: sessões ordenadas, falantes, datas, captions e evidências. Preservar timestamps textuais quando não houver conversão segura; não substituir datas inválidas por epoch.
- Tratar respostas adversariais e abstention conforme o protocolo original; não usar adversarial_answer automaticamente como resposta correta.

### Critério de aceite

Teste de inferência isolada e regressões com pequenas amostras no formato oficial; nenhuma informação de referência entra no prompt de observação ou resposta. Datas e falantes sobrevivem à normalização. Reexecutar os seis casos antigos apenas para verificar a infraestrutura.

## 2. Instrumentar a perda de informação

### Entregas

Persistir por execução: hash do dataset, IDs dos casos, configuração, modelo, versões dos prompts, eventos normalizados, itens extraídos, contexto projetado, resposta, avaliação, usage e latências separadas por etapa.

Separar quatro possíveis falhas:

1. ingestão: o fato de suporte não chegou corretamente ao observer;
2. extração: chegou, mas não entrou na memória;
3. projeção/recuperação: está na memória, mas não no contexto;
4. resposta: está no contexto, mas o answerer errou.

Usar evidências anotadas somente na análise posterior, nunca para selecionar o contexto do sistema avaliado. Relatar referências de sessão e de turno separadamente.

### Critério de aceite

Cada erro dos seis casos iniciais tem artefatos e uma classificação sustentada por inspeção, sem assumir antecipadamente que a culpa é da extração.

## 3. Implementar o fluxo online de TOM

### Entregas

- Processar sessões e chunks limitados por tokens, preservando ordem, identidade e datas; política explícita para evento maior que o limite.
- Persistir eventos e memórias usando o ledger/store já existentes; atualizar métricas de forma cumulativa.
- Observar cada histórico uma vez e reutilizar o estado imutável nas perguntas correspondentes. Cache pela identidade/hash do histórico, modelo e configuração, não pela resposta esperada.
- Manter ingestão independente da pergunta. Aplicar recuperação orientada pela pergunta apenas na leitura, reutilizando os componentes existentes.
- Medir retenção no ledger e seleção no contexto separadamente. Ligar consolidação/recall apenas quando o diagnóstico mostrar necessidade; fazer ablação de cada mudança.
- Registrar overflow de memórias EXACT como falha explícita; não descartar restrições silenciosamente nem aumentar orçamento só para TOM.

### Critério de aceite

Sem reobservar a mesma conversa por pergunta; nenhuma chamada contém o histórico inteiro acima do limite; fontes válidas e orçamento auditável. Casos de regressão cobrem isolamento entre conversas e contabilização cumulativa.

## 4. Tornar a comparação válida

### Implementação atual

A comparação agora tem contratos explícitos:

- `FullContextMemory` é o controle genuíno e nunca corta contexto. Se exceder o
  orçamento declarado, a linha é marcada como `comparison_valid=false` e
  `failure=context_over_budget`; ela não recebe uma pontuação artificial.
- `TruncatedFullContextMemory` é um controle diferente e registra
  `context_truncated=true`; não deve ser agregado ao full-context genuíno.
- Todas as estratégias usam o mesmo answerer, orçamento final e scorer. O uso
  do answerer é zerado antes de cada chamada para não reutilizar usage antigo.
- Cada linha registra `context_policy`, `context_truncated`,
  `context_over_budget`, `comparison_valid`, `failure`, implementação efetiva e
  versão do avaliador.
- `exact_match` é igualdade normalizada (`normalized-equality-v1`).
  `substring_match` é apenas diagnóstico e nunca accuracy.
- Os eventos LoCoMo preservam falante no conteúdo e nos metadados; a data da
  pergunta LongMemEval é enviada ao answerer.

`ObservationalMemory` e `KnowledgeTriageMemory` continuam explicitamente
marcadas como `*_smoke`: não são reproduções dos trabalhos. `RecursiveSummaryMemory`
é o ponto de injeção para uma baseline de resumo recursivo via LLM e não é
ativada sem um summarizer.

Esta etapa torna a comparação auditável, mas não transforma as smoke baselines
em implementações oficiais. Avaliadores oficiais versionados e reproduções
fiéis dos papers continuam pré-requisitos para uma comparação científica final.

### Entregas

- Integrar avaliadores oficiais com versão fixada e saídas compatíveis. Separar geração de respostas e julgamento para permitir reavaliar sem nova ingestão.
- Corrigir exact_match para igualdade normalizada; nomear substring como métrica diagnóstica, nunca accuracy oficial.
- Adicionar full-context genuíno, sem truncamento silencioso, quando couber na janela. Rotular separadamente contexto truncado com orçamento fixo.
- Implementar baseline de resumo recursivo com LLM; não chamar seleção de eventos recentes de resumo.
- Conectar implementações oficiais ou reproduções documentadas de Observational Memory e Knowledge Triage. Manter heurísticas atuais apenas como smoke baselines com nomes explícitos.
- Usar mesmo answerer, orçamento de contexto final e política de ingestão nas comparações controladas; registrar diferenças necessárias entre os métodos. Separar reprodução nativa de comparação com backbone comum.

### Critério de aceite

Tabela compara métodos identificáveis, não proxies com nomes de papers. Judge, prompts, categorias, abstention, falhas e critérios de agregação documentados. Custo/latência incluem ingestão, leitura/resposta e julgamento separadamente.

## 5. Piloto controlado e ablações

### Desenho

Fixar antes das execuções um manifesto de desenvolvimento e outro de avaliação, sem selecionar casos favoráveis. No LoCoMo separar por conversa, evitando vazamento entre perguntas do mesmo histórico; no LongMemEval estratificar por categoria e verificar históricos compartilhados.

Começar com cerca de 30–50 perguntas distribuídas entre categorias e históricos para medir execução e localizar falhas, não para sustentar o paper. Definir teto de chamadas/tempo e respeitar rate limits da assinatura. Salvar resultados incrementalmente, permitir resume e não pontuar erro de infraestrutura como resposta incorreta silenciosamente.

Comparações graduais:

1. full-context vs resumo recursivo vs TOM;
2. TOM sem tipagem vs com tipagem, mantendo extração e orçamento comparáveis;
3. TOM com/sem recuperação orientada pela pergunta;
4. TOM vs OM e Knowledge Triage fiéis, quando disponíveis.

Orçamentos iniciais: 2k, 4k e 8k tokens; começar por 4k e ampliar depois de validar o piloto. Medir qualidade por categoria, abstention, taxa de falha, evidência preservada, tokens reais, armazenamento, chamadas e latências p50/p95. Separar custo de ingestão por histórico e custo amortizado por pergunta.

### Critério de aceite

Relatório identifica a fronteira qualidade versus consumo, mostra pares de casos e incerteza. Intervalos no LoCoMo respeitam agrupamento por conversa; poucos grupos limitam conclusões. Ganho não é pré-condição para encerrar: resultado negativo também deve ser registrado.

## Implementação da etapa 5

O piloto controlado agora tem ferramentas determinísticas para congelar a amostra,
separar histórias e retomar execuções:

```bash
PYTHONPATH=src python -m tom.benchmarks.pilot create locomo data/locomo10.json \
  --output results/locomo-pilot --max-cases 40
PYTHONPATH=src python -m tom.benchmarks.public_cli locomo data/locomo10.json \
  --manifest results/locomo-pilot/development.json --budget 4096 \
  --output results/locomo-pilot/development --resume --max-calls 40
PYTHONPATH=src python -m tom.benchmarks.pilot report results/locomo-pilot/development
```

O manifesto usa hash do dataset, seleção estável sem olhar respostas e a história
como unidade de split. O runner grava cada caso imediatamente, pode continuar com
`--resume`, limita chamadas com `--max-calls` e o resumo separa qualidade válida,
falhas, abstention, tokens, armazenamento e p50/p95 de latência. `--budget 2048`,
`4096` e `8192` permitem repetir o piloto nos três orçamentos previstos.

## 6. Experimento para o paper

Após congelar configuração e protocolo, executar splits públicos completos, reportando versão, configuração, exclusões e taxa de falhas. Repetir execuções conforme variância e orçamento permitirem; não ajustar prompts no conjunto final.

Executar também compaction-cliff com compactação efetiva nos ciclos 1, 2, 4, 8, 16 e 32, e testes comportamentais de restrições/procedimentos. QA conversacional não testa sozinha a hipótese de preservação de conhecimento de agentes de código.

Conclusão deve distinguir: melhoria de QA, preservação sob compactação e eficiência. Não alegar superioridade geral a partir de uma única métrica. Publicar manifestos, scripts, resultados e limitações, respeitando licenças dos datasets e implementações.

### Reprodução do benchmark de referência (Knowledge Triage, CIKM'26)

O paper que motivou a comparação (`searchsim-org/cikm26-knowledge-triage`,
https://github.com/searchsim-org/cikm26-knowledge-triage) não usa LoCoMo/LongMemEval
como benchmark principal. Ele mede preservação por tipo (constraint/procedural/
belief/preference/episodic) sob compactação de configs de agente reais
(AgentArtifactCorpus), com dois experimentos centrais:

- Table 6 (Compaction Cliff): 5 rounds sequenciais de compactação a 50%,
  medindo recall de constraints contra o conjunto ORIGINAL.
- Table 7 (compression curves): compactação single-shot a 50%/25%/10%.

Instalamos o pacote oficial `knowledge-triage` (via git, pinado ao commit usado
neste projeto) como dependência, para reutilizar `type_compact`, o classificador
regex e a função de preservação por tipo exatamente como no paper — garantindo
que os números do TypeCompact aqui reproduzido sejam comparáveis aos do paper,
não uma reimplementação sujeita a divergência silenciosa.

```bash
PYTHONPATH=src python -m tom.benchmarks.knowledge_triage_repro \
  --data-dir data/aac/sample --n 20 --seed 11 \
  --table both --ratios 0.50,0.25,0.10 --rounds 5 --ratio 0.50 \
  --parallel 8 --output results/knowledge-triage-repro
```

`data/aac/sample` é a amostra estratificada de 327 artefatos (327 arquivos,
34 estratos) publicada no próprio repositório do paper; os 20 configs
selecionados pela função `load_configs` seguem o mesmo estrato E2 (800–30000
caracteres, pelo menos uma constraint) e a mesma seed (11) usados no paper,
então os resultados de TypeCompact aqui devem cair dentro da variância de
amostragem dos números publicados em
`docs/reference-knowledge-triage-multiturn_stability.json` e
`docs/reference-knowledge-triage-compression_curves.json`.

O script adiciona duas colunas que o repositório upstream não tem:

- `vanilla_llm`: o mesmo baseline de compactação vanilla do paper, mas rodando
  através do provedor Codex deste projeto em vez de GPT-5.4/Sonnet — controla
  para diferença de modelo, não de metodologia.
- `tom`: o próprio ciclo `ingest → observe → compact → context` do TOM usado
  como compressor texto→texto. A recuperação condicionada por query é
  desligada (`use_retrieval=False`) porque esta tarefa não tem query — é
  compactação pura por orçamento, o mesmo papel que `type_compact` desempenha.
  Abaixo do orçamento mínimo seguro (B_min), em vez de falhar (como
  `ContextProjector` faz por padrão), o script cai para renderizar todo o
  conteúdo protegido incondicionalmente — o mesmo comportamento best-effort
  que `type_compact` retorna sob `COMPACTION_UNSAFE`.

Achado e correção (n=20, ver `results/knowledge-triage-repro/`): a primeira
execução mostrou TOM perdendo recall de constraint mesmo com classificação de
tipo correta, porque `TypedObserver` fazia o LLM reescrever o texto durante a
observação — `RetentionPolicy.EXACT`/`HIGH_FIDELITY` só controlava prioridade
de retenção no orçamento, nunca obrigou o conteúdo armazenado a ser o texto de
origem. Corrigido em `enforce_verbatim_content` (`src/tom/observer/typed_observer.py`):
para itens `EXACT`/`HIGH_FIDELITY`, o conteúdo é substituído pelo texto dos
eventos-fonte citados após a extração; o LLM continua responsável apenas por
classificar (tipo/retenção/importância/escopo), não por reescrever o que deve
sobreviver à compactação.

Resultado após a correção, recall de constraint no Compaction Cliff (5 rounds
a 50%, mesmos 20 configs, seed 11):

| round | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|
| TypeCompact (paper) | 1.00 | 0.96 | 0.96 | 0.96 | 0.96 |
| TypeCompact (nosso) | 1.00 | 0.97 | 0.85 | 0.83 | 0.83 |
| gpt-5.4-mini (paper) | 0.48 | 0.28 | 0.18 | 0.12 | 0.10 |
| vanilla_llm (nosso) | 0.75 | 0.36 | 0.15 | 0.09 | 0.07 |
| TOM antes da correção | 0.24 | 0.06 | 0.02 | 0.02 | 0.01 |
| TOM depois da correção | 0.73 | 0.45 | 0.24 | 0.20 | 0.15 |

TOM passou de muito abaixo de ambos os baselines vanilla para superá-los a
partir do round 2, permanecendo abaixo de TypeCompact — esperado, já que
`type_compact` é determinístico e fatia o texto original em vez de usar um
LLM. Qualquer alegação de superioridade de TOM sobre Knowledge Triage ainda
precisa considerar esse trade-off explicitamente e reportar n pequeno (20
configs) com intervalo de confiança antes de qualquer conclusão para o paper.

### Isolando classificação LLM vs mecanismo de observação/compactação

Pergunta seguinte: o gap restante entre TOM (LLM) e TypeCompact vem do
mecanismo assíncrono observe→compact→project em si, ou só da classificação
por LLM ser mais ruidosa que o classificador regex do paper? Para isolar,
`src/tom/observer/deterministic_observer.py` implementa o mesmo protocolo
`Observer` usado por `TypedTOMMemory`, mas classifica com
`knowledge_triage.classifier.classify_instruction` (o próprio regex do paper)
em vez de um LLM — zero chamadas de rede, determinístico, sem paraphrase (o
classificador só rotula, nunca reescreve). É a ideia de observational memory
(observar em background, por chunk, guardar tipado, montar contexto na
compactação) com a classificação determinística do paper no lugar do LLM.

Ligado como quarto braço `tom_deterministic` em `knowledge_triage_repro.py`,
reusando o mesmo `TypedTOMMemory`/`ContextProjector` que o braço `tom`:

| round | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|
| TypeCompact (paper) | 1.00 | 0.96 | 0.96 | 0.96 | 0.96 |
| TypeCompact (nosso) | 1.00 | 0.97 | 0.85 | 0.83 | 0.83 |
| gpt-5.4-mini (paper) | 0.48 | 0.28 | 0.18 | 0.12 | 0.10 |
| vanilla_llm (nosso) | 0.70 | 0.37 | 0.25 | 0.19 | 0.15 |
| tom (classificação LLM) | 0.76 | 0.53 | 0.24 | 0.18 | 0.16 |
| tom_deterministic | 1.00 | 0.97 | 0.84 | 0.75 | 0.73 |

`tom_deterministic` reproduz TypeCompact quase inteiro (0.73 vs 0.83 no round
5, ambos bem acima dos baselines vanilla e do `tom` com LLM) e roda em
milissegundos, sem custo de API. Isso confirma que o mecanismo de
observação/compactação assíncrona do TOM não é o limitante: o gap vinha quase
todo da classificação por LLM, não do design do pipeline. Reforça que qualquer
comparação futura com Knowledge Triage deveria reportar os três braços
(`tom_deterministic`, `tom`, `vanilla_llm`) lado a lado, não só `tom` vs
vanilla, para não confundir "classificador ruim" com "arquitetura ruim".

## Ordem de execução

1 → 2 → 3 → 4 → 5 → 6. Não executar novamente os datasets completos antes das etapas 1–4. Sem integração de memória ao Pi: reutiliza-se apenas o transporte/autenticação para inferência Codex.
