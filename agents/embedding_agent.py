import numpy as np

class EmbeddingAgent:
    def generate_embedding(self, text):
        # placeholder: simula um vetor
        return np.random.rand(512).tolist()

if __name__ == "__main__":
    agent = EmbeddingAgent()
    emb = agent.generate_embedding("chicken recipe")
    print(emb[:10], "...")  # imprime só os 10 primeiros valores