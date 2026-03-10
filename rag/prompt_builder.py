def build_prompt(question, context):
    return f"Context:\n{context}\n\nQuestion:\n{question}\nAnswer:"