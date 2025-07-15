import numpy as np
from llama_cpp import Llama
from chat.chat_manager import load_model_path  # ou defina diretamente o caminho do modelo

class EmbeddingHandler:
    def __init__(self):
        model_path = load_model_path()
        self.model = Llama(
            model_path=model_path,
            embedding=True,
            n_ctx=2048  # ✅ aumenta a janela de contexto
        )

    def embeddar(self, texto):
        try:
            resposta = self.model.embed(texto)
            emb = None

            if isinstance(resposta, dict) and "data" in resposta:
                emb = resposta["data"][0].get("embedding") or resposta["data"][0].get("data")
            elif isinstance(resposta, dict) and "embedding" in resposta:
                emb = resposta["embedding"]
            elif isinstance(resposta, list):
                if isinstance(resposta[0], float):
                    emb = resposta
                elif isinstance(resposta[0], list):
                    emb = resposta[0]

            if emb is None:
                raise ValueError("Embedding retornado em formato inesperado.")

            return np.array(emb, dtype=np.float32)

        except Exception as e:
            print(f"Erro ao gerar embedding com LLaMA: {e}")
            return np.zeros(4096, dtype=np.float32)

