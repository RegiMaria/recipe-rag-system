import numpy as np

"""
04- O EmbeddingAgent é o tradutor semântico do pipeline.Ele converte texto legível por humanos em vetores numéricos 
que máquinas conseguem comparar por significado.
O que ele faz:
Recebe os chunks estruturados do ProcessingAgent e para cada um gera um vetor denso (embedding) que representa
o significado semântico daquele texto.
Esses vetores são armazenados num banco vetorial.
"""

class EmbeddingAgent:
    def generate_embedding(self, text):
        # placeholder: simula um vetor
        return np.random.rand(512).tolist()

if __name__ == "__main__":
    agent = EmbeddingAgent()
    emb = agent.generate_embedding("chicken recipe")
    print(emb[:10], "...")  # imprime só os 10 primeiros valores