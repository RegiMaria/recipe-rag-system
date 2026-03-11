# Placeholder
Nível de ingestão
Função:  limpar e converter texto bruto em dados estruturados
Quem chama: processing_agent.py (via prompt_builder).
Por que a dependência: O processing_agent recebe o HTML sujo do collector_agent. Ele não sabe o que é "ruído" (anúncios, menus de navegação, rodapés). Este prompt instrui o modelo a ignorar o lixo e manter apenas o conteúdo textual relevante da receita.
