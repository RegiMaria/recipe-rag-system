

"""
O RAG Agent é o ponto de chegada do pipeline. Ele une tudo que foi preparado pelos agentes anteriores para responder
perguntas com precisão e embasamento.
RAG significa Retrieval-Augmented Generation: primeiro recupera contexto relevante,
depois gera a resposta com base nesse contexto.
"""


class RAGAgent:
    def answer(self, question, context_chunks):
        # placeholder simples
        context_text = "\n".join([c["text"] for c in context_chunks])
        return f"Question: {question}\nAnswer based on context:\n{context_text}"

if __name__ == "__main__":
    rag = RAGAgent()
    answer = rag.answer("Chicken recipes?", [{"text": "Garlic Chicken recipe"}])
    print(answer)