# Architecture Decision Records #
## ADR-002-arquitetura-orientada-prompts ##

Data: 11-03-2026

## Separar os prompts em arquivos .md: ##

Arquitetura orientada  a prompts;

**Por que usar arquivos .md para Prompts?**

1. Versionamento (Git): Se a gente mudar uma instrução no prompt ("Seja mais educada" ou "Responda apenas em JSON"), o Git registra exatamente o que mudou, quem mudou e por quê.

2. Limpeza de Código: Arquivos .py (como o rag_agent.py) ficam limpos. Eles cuidam da lógica (abrir conexão, buscar no banco), enquanto o arquivo .md cuida da "personalidade" da IA.

3.  Separar a Inteligência (Prompts) da Engenharia (Agents) e da Orquestração (Airflow) estruturalmente.



:small_orange_diamond:**Status de maturidade**

:small_orange_diamond:Arquitetura atual -  antes de organizar prompts
```

Sites de Receitas (YAML config)
    ↓
Crawler Agent → Descobre URLs
    ↓
Collector Agent → Baixa HTML
    ↓
Processing Agent → Extrai dados
    ↓
Chunking Module → Divide em chunks
    ↓
Embedding Agent → Gera vetores
    ↓
Storage Layer → GCS + BigQuery
    ↓
RAG Pipeline → Busca + geração de resposta

Orquestracao: Apache Airflow DAG com agendamento diario.
```

:small_orange_diamond:**Estrutura de Arquivos atual**

| Caminho | Propósito |
|--------|-----------|
| `agents/crawler_agent.py` | Rastreia URLs de receitas com filtros por palavra-chave |
| `agents/collector_agent.py` | Baixa HTML com retry e timestamps |
| `agents/processing_agent.py` | Parseia HTML com BeautifulSoup e extrai dados estruturados |
| `agents/embedding_agent.py` | Placeholder — integraria com Vertex AI |
| `agents/rag_agent.py` | Placeholder — geração de respostas com LLM |
| `rag/chunking.py` | Chunking semântico em 3 tipos: metadata, ingredientes, instruções |
| `rag/retriever.py` | Placeholder — busca no BigQuery por similaridade |
| `rag/generator.py` | Placeholder — monta resposta final |
| `rag/prompt_builder.py` | Concatena contexto + pergunta |
| `storage/gcs_client.py` | Placeholder — upload para Google Cloud Storage |
| `storage/bigquery_client.py` | Placeholder — armazena embeddings |
| `pipeline/airflow_dag.py` | DAG Airflow: crawl → collect → process → embed |
| `config/sources.yaml` | Lista de sites (tudogostoso, panelinha, etc.) |
| `config/categories.yaml` | Categorias semânticas com marcadores e exclusões |



:small_orange_diamond:**Status de Maturidade atual**

| Componente | Status |
|-------------|--------|
| Crawler | Funcional |
| Collector | Funcional (com retry) |
| Processing | Funcional (multi-seletor CSS) |
| Chunking | Pronto para produção |
| Categories config | Bem definido |
| Embedding (Vertex AI) | Placeholder (vetor aleatório) |
| RAG retriever/generator | Placeholder |
| Storage (GCS / BigQuery) | Placeholder |

:small_orange_diamond:Pontos Fortes


* Separação clara de responsabilidades entre agentes
* Chunking semântico sofisticado (metadata + ingredientes atomicos + instrucoes por sentenca)
* Configuracao externalizada em YAML (fontes e categorias)
* Regras de exclusao por categoria (ex: vegetariano proibe carnes/peixes)
* Pipeline Airflow bem estruturado com XCom para passar dados entre tasks


  :small_orange_diamond:Gaps / Próximos Passos Naturais


1. Integracao com Vertex AI — embedding real no embedding_agent.py
2. Clientes GCS/BigQuery — implementar upload e busca vetorial
3. RAG retriever/generator — conectar ao LLM para respostas reais
4. Classificacao por categoria — usar o categories.yaml durante o processamento
5. Testes — nao ha testes automatizados ainda



**Reorganização da Estrutura de Pastas:**

Arquitetura orientada a prompts

