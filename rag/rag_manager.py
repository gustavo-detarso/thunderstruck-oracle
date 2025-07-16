import numpy as np
from rag.retriever import Retriever
from rag.embedding_handler import EmbeddingHandler
import os

# Importe a função busca_tabela_estruturada corretamente.
from chat.chat_manager import busca_tabela_estruturada

class RAGManager:
    def __init__(self, model=None):
        self.retriever = Retriever()
        self.emb_handler = EmbeddingHandler()
        self.model = model or self.emb_handler.model  # pega da instância
        self.max_tokens = 1500  # pode ajustar baseado no modelo local

    def responder_pergunta(self, pergunta, tags=None, return_score=False, temperature=0.5):
        # === Busca tabular estruturada antes de tudo ===
        tabular_resultado = busca_tabela_estruturada(pergunta)
        # tabular_resultado pode ser (lista, estado, fonte_csv) ou None
        if (
            tabular_resultado and
            isinstance(tabular_resultado, tuple) and
            isinstance(tabular_resultado[0], list) and
            len(tabular_resultado[0]) > 0
        ):
            lista, estado, fonte_csv = tabular_resultado
            fontes = [fonte_csv]  # mostra o nome real do arquivo fonte
            if return_score:
                return (lista, estado), fontes, 1.0
            return (lista, estado)
        # === FIM DO PATCH ===

        # Gera embedding da pergunta
        emb = self.emb_handler.embeddar(pergunta)

        # Busca documentos relevantes
        documentos = self.retriever.buscar(emb, tags=tags)

        # Gera o contexto com os documentos recuperados
        contexto = self._montar_contexto(documentos)

        # Gera a resposta com o modelo local
        resposta = self._gerar_resposta(pergunta, contexto, temperature)

        # Estima confiabilidade
        score = self._estimar_score(documentos)

        fontes = list(dict.fromkeys(doc[1].get("fonte", "Desconhecida") for doc in documentos if doc[1]))

        if return_score:
            return resposta, fontes, score
        return resposta

    def _montar_contexto(self, documentos):
        contexto = ""
        for doc, meta, dist in documentos:
            trecho = f"[Fonte: {meta.get('fonte', 'Desconhecida')}]\n{doc.strip()}\n"
            contexto += trecho + "\n\n"
        return contexto.strip()

    def _gerar_resposta(self, pergunta, contexto, temperature=0.5):
        prompt = f"""Responda com base no contexto abaixo. Seja claro, objetivo e cite as fontes quando possível.

### CONTEXTO:
{contexto}

### PERGUNTA:
{pergunta}

### RESPOSTA:"""

        resposta = self.model(prompt)
        return resposta["choices"][0]["text"].strip()

    def _estimar_score(self, documentos):
        if not documentos:
            return 0.0
        distancia = documentos[0][2]
        score = max(0.0, min(1.0, 1 - distancia))
        return score

