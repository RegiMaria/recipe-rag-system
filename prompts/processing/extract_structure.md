# Placeholder
Nível de ingestão
Quem chama: processing_agent.py (imediatamente após a limpeza).
Por que a dependência: Dados não estruturados não podem ser filtrados no BigQuery (ex: "receitas com menos de 500kcal"). Este prompt obriga o LLM a extrair campos específicos: titulo, ingredientes (lista), passo_a_passo, tempo_preparo, calorias e categoria.
Resultado: Gera o JSON que o embedding_agent usará para criar os vetores.