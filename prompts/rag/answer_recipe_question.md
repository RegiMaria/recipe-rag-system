# Placeholder
Nível de Entrega
Quem chama: rag_agent.py (o agente de interface final).
Por que a dependência: Quando o usuário pergunta "Tenho frango e limão, o que faço?", o retriever.py busca as receitas similares no BigQuery. O rag_agent então combina:

A pergunta do usuário.

O conteúdo das receitas encontradas.

Este Prompt.

Função do Prompt: Define a persona, o tom de voz e, crucialmente, as Groundedness Rules (regras de pé no chão): "Responda apenas com base nas receitas fornecidas; se não souber, não invente".
