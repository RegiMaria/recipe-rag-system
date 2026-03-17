# Architecture Decision Records #
## ADR-004-Validação-Pipeline-NLP ##

Data: 17-03-2026

## Validação de Pipeline NLP ##

**Contexto e Objetivo**

Antes de mover a infraestrutura para a nuvem (Google Cloud Platform), decidimos validar o motor lógico do `ProcessingAgent` em ambiente local (WSL/Ubuntu). O objetivo foi garantir que as etapas de limpeza de HTML, extração de ingredientes e classificação semântica estivessem robustas sem incorrer em custos de API ou latência de rede durante a fase de depuração.

**A Abordagem "Local-First"**
Utilizamos bibliotecas de código aberto e modelos pré-treinados para simular o comportamento do sistema final:

**spaCy (Lematização):** Validamos a capacidade do agente de normalizar termos culinários (ex: converter plurais e flexões para a forma raiz), essencial para a precisão dos filtros.

**Sentence-Transformers (HuggingFace):** Implementamos o modelo paraphrase-multilingual-MiniLM-L12-v2 localmente para testar a similaridade semântica. Isso provou que o agente consegue entender que "filé de frango" e "peito de frango" pertencem ao mesmo contexto gastronômico.

**Resultados Obtidos**
O teste local foi bem-sucedido, confirmando que:

O parser de ingredientes consegue isolar quantidade, unidade e nome com alta precisão.

A lógica de categorização (Fitness, Vegana, etc.) funciona através de scoring semântico, e não apenas por palavras-chave rígidas.

O pipeline de dados está devidamente estruturado para o próximo estágio.

**Próximo Passo:** Transição para GCP
Com a lógica validada, a arquitetura agora evolui para o ambiente de produção na nuvem:

**Vertex AI:** Substituirá o processamento local de embeddings por modelos de larga escala (text-multilingual-embedding), garantindo escalabilidade e integração nativa.

**BigQuery:** Atuará como nossa memória estruturada e vetorial, consolidando o conhecimento gastronômico para alimentar o sistema RAG.