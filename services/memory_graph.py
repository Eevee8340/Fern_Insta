import numpy as np
from sklearn.decomposition import PCA
from typing import Dict, Any, List
import random

class MemoryGraphService:
    def process_graph_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        ids = raw_data.get('ids')
        if ids is None: ids = []
        
        embeddings = raw_data.get('embeddings')
        if embeddings is None: embeddings = []
        
        metadatas = raw_data.get('metadatas')
        if metadatas is None: metadatas = []
        
        documents = raw_data.get('documents')
        if documents is None: documents = []

        print(f"   [Graph] Raw counts - IDs: {len(ids)}, Embeddings: {len(embeddings) if len(embeddings) > 0 else 'None'}")

        if len(ids) == 0 or len(embeddings) == 0:
            return {"nodes": [], "links": []}

        # Validate Data Consistency
        valid_indices = []
        valid_embeddings = []
        
        for i, emb in enumerate(embeddings):
            if emb is not None and len(emb) > 0:
                valid_indices.append(i)
                valid_embeddings.append(emb)
        
        n_samples = len(valid_indices)
        print(f"   [Graph] Valid samples after filtering: {n_samples}")

        if n_samples == 0:
            return {"nodes": [], "links": []}

        # 1. Dimensionality Reduction (PCA)
        try:
            matrix = np.array(valid_embeddings)
            
            # If less than 3 samples, fallback to random
            if n_samples < 3:
                coords = np.random.rand(n_samples, 3) * 50
            else:
                pca = PCA(n_components=3)
                coords = pca.fit_transform(matrix)
        except Exception as e:
            print(f"   [Graph] PCA Error: {e}")
            # Fallback to random if PCA fails
            coords = np.random.rand(n_samples, 3) * 50

        # 2. Build Nodes
        nodes = []
        for idx, i in enumerate(valid_indices):
            # i is index in original raw_data lists
            # idx is index in coords/valid_embeddings
            
            meta = metadatas[i] if metadatas and i < len(metadatas) else {}
            if meta is None: meta = {}
            
            nodes.append({
                "id": ids[i],
                "text": documents[i] if documents and i < len(documents) else "",
                "user": meta.get("user", "unknown"),
                "source": meta.get("source", "unknown"),
                "fx": float(coords[idx][0] * 50), 
                "fy": float(coords[idx][1] * 50),
                "fz": float(coords[idx][2] * 50),
                "group": meta.get("source", "default")
            })

        # 3. Build Links
        links = []
        try:
            from sklearn.neighbors import NearestNeighbors
            if n_samples > 1:
                k = min(n_samples, 4) 
                nbrs = NearestNeighbors(n_neighbors=k, algorithm='ball_tree').fit(coords)
                distances, indices = nbrs.kneighbors(coords)

                for i in range(n_samples):
                    for j in indices[i]:
                        if i != j:
                            links.append({
                                "source": nodes[i]["id"],
                                "target": nodes[j]["id"]
                            })
        except Exception as e:
            print(f"   [Graph] Linking Error: {e}")

        print(f"   [Graph] Generated {len(nodes)} nodes and {len(links)} links.")
        return {"nodes": nodes, "links": links}

memory_graph_service = MemoryGraphService()