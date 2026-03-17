# Architecture Decision Records #
## ADR-001-angChain ##

Data: 10-03-2026

## 1.Uso de LangChain:##

O Langchain é o motor de execução dos agentes.

O Airflow é o motor de agendamento que decide quando esses motores devem ligar.

**O Airflow diz:** "Agente de Processamento, acorde! Tem 50 receitas novas no GCS."
**O Agente (via LangChain)** acorda, usa o Vertex AI para entender a receita, transforma em vetor e guarda no BigQuery.

Sem LangChain: Eu teria que configurar manualmente a autenticação, tratar o JSON de resposta do Vertex AI, gerenciar o histórico da conversa e fazer a busca SQL no BigQuery "na mão". 

## 2. O que é cobrado: ##

**Vertex AI (Google Cloud):** Quando o LangChain pede para o Gemini processar uma receita, o Google vai te cobrar pelos tokens usados.
**BigQuery:** O armazenamento e a busca vetorial têm o custo normal da Google Cloud.

| Componente | Como o LangChain atua | O que ele faz na prática |
|-------------|----------------------|---------------------------|
| **Processing Agent** | `RecursiveCharacterTextSplitter` | Divide a receita bruta do GCS em chunks menores e adequados para processamento por LLM. |
| **Embedding Agent** | `VertexAIEmbeddings` | Converte o texto em vetores usando Vertex AI e prepara os embeddings para armazenamento no BigQuery. |
| **RAG Agent** | `VectorStoreRetriever` + `ChatVertexAI` | Busca receitas similares no BigQuery e monta o prompt final para o LLM gerar a resposta. |
| **Ferramentas (Tools)** | `BaseTool` | Converte funções Python (ex: buscar calorias) em ferramentas que o agente pode decidir utilizar. |