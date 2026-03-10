import json

class RecipeChunker:
    def __init__(self, max_instruction_step_chars=500):
        self.max_instruction_step_chars = max_instruction_step_chars

    def create_chunks(self, recipe_data):
        """
        Recebe um dicionário: 
        {
          "title": "Bolo de Cenoura",
          "ingredients": ["3 cenouras", "4 ovos", ...],
          "instructions": "1. Bata tudo no liquidificador. 2. Asse por 40min...",
          "metadata": {"source": "TudoGostoso", "category": "dessert"}
        }
        """
        chunks = []

        # --- CHUNK 1: Identidade e Metadados ---
        # Essencial para buscas por título ou categoria
        header_chunk = {
            "type": "metadata",
            "text": f"Receita: {recipe_data.get('title')}\n"
                    f"Fonte: {recipe_data.get('metadata', {}).get('source')}\n"
                    f"Categoria: {recipe_data.get('metadata', {}).get('category')}"
        }
        chunks.append(header_chunk)

        # --- CHUNK 2: Bloco de Ingredientes (ATÔMICO) ---
        # Nunca quebramos a lista de ingredientes para não perder o contexto das proporções
        ingredients_list = "\n".join(recipe_data.get('ingredients', []))
        ingredients_chunk = {
            "type": "ingredients",
            "text": f"Ingredientes para {recipe_data.get('title')}:\n{ingredients_list}"
        }
        chunks.append(ingredients_chunk)

        # --- CHUNK 3: Passo a Passo (SEMÂNTICO) ---
        # Aqui podemos quebrar se o modo de preparo for uma "bíblia", 
        # mas sempre respeitando o fim de uma frase ou instrução.
        instructions = recipe_data.get('instructions', "")
        
        # Se for muito grande, quebramos por sentenças ou parágrafos
        if len(instructions) > self.max_instruction_step_chars:
            steps = instructions.split('.') # Tenta quebrar em frases
            current_chunk = f"Instruções para {recipe_data.get('title')}:\n"
            
            for step in steps:
                if len(current_chunk) + len(step) < self.max_instruction_step_chars:
                    current_chunk += step.strip() + ". "
                else:
                    chunks.append({"type": "instructions_step", "text": current_chunk.strip()})
                    current_chunk = f"Instruções (cont.) {recipe_data.get('title')}: " + step.strip() + ". "
            chunks.append({"type": "instructions_step", "text": current_chunk.strip()})
        else:
            chunks.append({
                "type": "instructions_full",
                "text": f"Instruções para {recipe_data.get('title')}:\n{instructions}"
            })

        return chunks

if __name__ == "__main__":
    # Teste rápido
    sample_recipe = {
        "title": "Frango com Alho",
        "ingredients": ["500g de frango", "4 dentes de alho", "Azeite"],
        "instructions": "Corte o frango em cubos. Refogue o alho no azeite. Adicione o frango e doure.",
        "metadata": {"source": "Panelinha", "category": "fitness"}
    }
    
    chunker = RecipeChunker()
    result = chunker.create_chunks(sample_recipe)
    
    for i, c in enumerate(result):
        print(f"\n--- Chunk {i} ({c['type']}) ---")
        print(c['text'])