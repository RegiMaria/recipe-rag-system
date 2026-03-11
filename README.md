## Projeto: Rag recipe system

Descrição: 

Este projeto utiliza uma arquitetura de agentes para mapear, extrair e estruturar informações de ingredientes de receitas culinárias da web. Através de técnicas de RAG (Retrieval-Augmented Generation), transformamos dados não estruturados (blogs, PDFs e sites) em um motor de busca semântico capaz de responder perguntas complexas sobre gastronomia.

Objetivo: Demonstrar um sistema RAG (Retrieval-Augmented Generation) com agentes especializados, ingestão de dados e busca semântica.

# O Problema:
As receitas na internet sofrem com a fragmentação. Estão presas em formatos variados (HTML, PDF), sem padronização nutricional e dependentes de buscas por palavras-chave que ignoram o contexto nutricional ou a intenção real do usuário.

# A Solução

Criamos um pipeline orquestrado que:

1.Descobre receitas autonomamente.

2.Estrutura ingredientes e modos de preparo usando NLP.

3.Indexa o conteúdo em um espaço vetorial para buscas semânticas.

4.Responde consultas complexas (ex: "Jantar rápido com frango e baixo carboidrato") utilizando LLMs.

# Arquitetura do Sistema

O fluxo de dados é desenhado para ser escalável e resiliente, utilizando o estado da arte em cloud computing:

Fluxo de Dados:

1. Ingestão: Crawlers exploram a web e armazenam o conteúdo bruto no Google Cloud Storage (Data Lake).

2. Processamento: O Apache Airflow dispara tarefas de limpeza, extração de entidades (ingredientes) e normalização.

3. Vetorização: Chunks de texto são transformados em embeddings via Vertex AI.

4. Armazenamento: Dados estruturados e vetores de alta dimensionalidade são salvos no BigQuery.

5. Serving: O Agente RAG processa a query do usuário, busca a similaridade no BigQuery e gera a resposta final.

# Stack Tecnológica

## 📦 Estrutura do Projeto

|  Caminho |  Propósito |
|:-----------|:-------------|
| `agents/crawler_agent.py` |  Rastreia URLs de receitas com filtros por palavra-chave |
| `agents/collector_agent.py` |  Baixa HTML com **retry** e **timestamps** |
| `agents/processing_agent.py` | Faz parsing do HTML com **BeautifulSoup** e extrai dados estruturados |
| `agents/embedding_agent.py` | Placeholder — futura integração com **Vertex AI** |
| `agents/rag_agent.py` |  Placeholder — geração de respostas com **LLM** |
| `rag/chunking.py` | Chunking semântico em 3 tipos: **metadata**, **ingredientes**, **instruções** |
| `rag/retriever.py` |  Placeholder — busca por similaridade no **BigQuery** |
| `rag/generator.py` |  Placeholder — monta a resposta final |
| `rag/prompt_builder.py` |  Concatena **contexto + pergunta** |
| `storage/gcs_client.py` |  Placeholder — upload para **Google Cloud Storage** |
| `storage/bigquery_client.py` |  Placeholder — armazenamento de **embeddings** |
| `pipeline/airflow_dag.py` |  DAG do **Airflow**: `crawl → collect → process → embed` |
| `config/sources.yaml` |  Lista de sites (Tudogostoso, Panelinha etc.) |
| `config/categories.yaml` |  Categorias semânticas com **marcadores e exclusões** |

# Arquitetura

  Sites de Receitas (Em YAML config)
          ↓
    [Crawler Agent]      → Descobre URLs de receitas
          ↓
    [Collector Agent]    → Baixa o HTML das paginas
          ↓
    [Processing Agent]   → Extrai titulo, ingredientes, instrucoes
          ↓
    [Chunking Module]    → Divide em chunks semanticos
          ↓
    [Embedding Agent]    → Gera vetores (Vertex AI)
          ↓
    [Storage Layer]      → Salva no GCS + BigQuery
          ↓
    [RAG Pipeline]       → Busca + Gera resposta via LLM

  Orquestracao: Apache Airflow DAG com agendamento diario.

## Tecnologias

- Apache Airflow
- Google Cloud Storage (GCS)
- BigQuery
- Vertex AI (embeddings e LLM)
- Python 3.10+

# Estrutura de diretórios

recipe-rag-system/
├── prompts/                      <-- Coração da IA
│   ├── processing/               <-- Prompts para limpar e converter texto bruto em dados estruturados (JSON).
│   │   ├── extract_structure.md
│   │   └── clean_text.md
│   └── rag/                      <-- Prompt principal que define a personalidade e as regras de resposta do assistente.
│       └── answer_recipe_question.md
├── agents/                       <-- Módulos autônomos com responsabilidades específicas
│   ├── crawler_agent.py          <-- Navega em sites descobre novas URLs
│   ├── collector_agent.py        <-- Realiza o download do conteúdo bruto (HTML) das páginas
│   ├── processing_agent.py       <-- Orquestra a limpeza e a estruturação dos dados - Consome prompts/processing/ 
│   ├── embedding_agent.py        <-- Transforma textos em vetores numéricos via Vertex AI
│   └── rag_agent.py              <-- Agente/interface recebe a dúvida do usuário coordena a busca e resposta usando prompts/rag/
├── rag/                          <-- Motor de inteligência da aplicação (by LangChain)
│   ├── chunking.py               <-- Divide as receitas em pedaços menores e logicamente coerentes
│   ├── retriever.py              <-- Realiza a busca por similaridade no banco vetorial
│   ├── generator.py              <-- Onde o LangChain/Vertex AI realmente "roda"
│   └── prompt_builder.py         <-- Utilitário que carrega e injeta variáveis nos arquivos de prompt `.md`
├── storage/                      <-- Camada de persistência e infraestrutura de dados
│   ├── gcs_client.py             <--Gerencia armazenamento de arquivos brutos e backups no Google Cloud Storage (Data Lake)
│   └── bigquery_client.py        <-- Interface para o Data Warehouse - metadados - busca vetorial
└── pipeline/                     <--Orquestração e automação
    └── airflow_dag.py            <-- Define o fluxo de trabalho (DAG), garante coleta processamento automático e monitorado.





# Os Agentes Especialistas

O sistema é composto por agentes com responsabilidades únicas:

🕵️ Crawler Agent: Navegação inteligente e descoberta de novas URLs.

📥 Collector Agent: Extração de conteúdo bruto e gestão de requests/proxies.

🧹 Processing Agent: Limpeza de ruídos (tags HTML, anúncios) e estruturação de ingredientes (NLTK/Spacy).

🔢 Embedding Agent: Transformação de receitas em representações matemáticas.

🧠 RAG Agent: O cérebro do sistema, que combina a busca vetorial com a fluidez do LLM.

# Como Executar o Projeto

Pré-requisitos

- Google Cloud Platform (GCP) Account ativa.

- Python 3.10 ou superior.

- Instância do Apache Airflow configurada.

# Instalação
Clone o repositório:

`git clone https://github.com/RegiMaria/recipe-rag-system.git`

# Instale as dependências:

`pip install -r requirements.txt`

# Configure as credenciais do GCP:

`export GOOGLE_APPLICATION_CREDENTIALS="caminho/para/seu/projeto.json"`

# Resultados Esperados
- Base de Conhecimento Viva: Atualização contínua via Airflow.

- Busca Semântica: Entendimento real de substituições de ingredientes e restrições alimentares.

- Escalabilidade: Capacidade de processar milhões de receitas com baixo custo de busca via BigQuery Vector Search.