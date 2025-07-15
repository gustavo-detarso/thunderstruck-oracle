import numpy as np
from rag.index_manager import carregar_index

class Retriever:
    def __init__(self):
        # Carrega índice FAISS, documentos e metadados
        self.index, self.docs, self.meta, self.emb_dim = carregar_index()

    def buscar(self, pergunta_emb_np, tags=None, k=20):
        """
        Busca os documentos mais semelhantes a partir de um embedding numpy.
        Retorna lista de tuplas: (documento, metadados, distância)
        """
        D, I = self.index.search(np.array([pergunta_emb_np]), k=k)
        resultados = []

        for idx, i in enumerate(I[0]):
            if i < len(self.docs):  # proteção contra índices inválidos
                doc = self.docs[i]
                metadados = self.meta[i]
                distancia = D[0][idx]
                if not tags or any(tag in metadados.get("tags", []) for tag in tags):
                    resultados.append((doc, metadados, distancia))

        return resultados

    def explorar_sem_pergunta(self, tags=None, limit=5):
        """
        Retorna documentos recentes com base nas tags solicitadas,
        ou os mais novos se não houver filtro.
        """
        if tags:
            docs_filtrados = [
                (doc, meta) for doc, meta in zip(self.docs, self.meta)
                if any(tag in meta.get("tags", []) for tag in tags)
            ]
        else:
            docs_filtrados = list(zip(self.docs, self.meta))

        # Ordena por data de criação (decrescente)
        docs_ordenados = sorted(
            docs_filtrados,
            key=lambda d: d[1].get("created_at", ""),
            reverse=True
        )

        return [d[0] for d in docs_ordenados[:limit]]

    def buscar_prioridade_portaria(self, pergunta_emb_np, k=20):
        """
        Busca por chunks das portarias de unidades, priorizando o TXT limpo,
        depois manual (regex) e por último tabular.
        Retorna lista de tuplas: (documento, metadados, distância)
        """
        prioridade_tags = [
            "portaria_unidades_txt",       # PRIMEIRO busca no txt limpo
            "portaria_unidades_manual",    # Depois busca regex/manual
            "portaria_unidades_tabular",   # Por último busca tabelas estruturadas
        ]
        for tag in prioridade_tags:
            resultados = self.buscar(pergunta_emb_np, tags=[tag], k=k)
            if resultados:
                # Retorna assim que encontrar pelo menos 1 chunk relevante
                return resultados
        # Se nada encontrado, retorna busca geral (sem filtro)
        return self.buscar(pergunta_emb_np, tags=None, k=k)

