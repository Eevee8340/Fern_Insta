import chromadb
from chromadb.config import Settings
import os
import uuid
import time
import consts
from typing import List, Dict, Any, Optional

class FernMemoryDB:
    def __init__(self, db_path: str = consts.MEMORY_DB_PATH) -> None:
        print(f"   [MemoryDB] Loading from {db_path}...")
        self.client = chromadb.PersistentClient(path=db_path)
        
        self.collection = self.client.get_or_create_collection(
            name="fern_long_term",
            metadata={"hnsw:space": "cosine"}
        )
        print(f"   [MemoryDB] Loaded {self.collection.count()} memories.")

    def add_memory(self, text: str, vector: List[float], source: str = "unknown", username: str = "unknown") -> None:
        # HEURISTIC FILTERS
        if not text or len(text.strip()) < 10:
            return

        # PRIVACY FILTER: Blacklist check
        # DEDUPLICATION & CONFLICT RESOLUTION (For Facts Only)
        if source == "strict_fact":
            existing = self.collection.query(
                query_embeddings=[vector],
                n_results=1,
                where={"$and": [{"source": "strict_fact"}, {"user": username}]}
            )
            
            if existing['distances'] and len(existing['distances'][0]) > 0:
                dist = existing['distances'][0][0]
                found_id = existing['ids'][0][0]
                
                # 1. Exact/Near Match (< 0.15): Refresh timestamp
                if dist < 0.15:
                    self.collection.update(
                        ids=[found_id],
                        metadatas=[{"source": source, "user": username, "timestamp": str(time.time())}]
                    )
                    print(f"\033[90m   [=] Fact Refreshed: {text[:40]}...\033[0m")
                    return
                
                # 2. Potential Conflict (< 0.35): Replace old with new
                # This handles "Alice likes blue" -> "Alice likes red"
                elif dist < 0.35:
                    self.collection.delete(ids=[found_id])
                    print(f"\033[93m   [-] Fact Overwritten (Conflict): {text[:40]}...\033[0m")
                    # Continue to add the new one below
            
        # Add to DB
        mem_id = str(uuid.uuid4())
        self.collection.add(
            documents=[text],
            embeddings=[vector],
            metadatas=[{"source": source, "user": username, "timestamp": str(time.time())}],
            ids=[mem_id]
        )
        print(f"\033[92m   [+] Memory Saved to DB: {text[:40]}...\033[0m")
    def get_all(self) -> List[Dict[str, Any]]:
        # Limit increased to 5000 to show more history
        try:
            data = self.collection.get(limit=5000, include=['documents', 'metadatas'])
            
            ids = data.get('ids')
            if ids is None: ids = []
            
            docs = data.get('documents')
            if docs is None: docs = []
            
            metas = data.get('metadatas')
            if metas is None: metas = []
            
            if len(ids) == 0: return []
            
            result = []
            for i in range(len(ids)):
                result.append({
                    "id": ids[i],
                    "text": docs[i] if i < len(docs) else "",
                    "meta": metas[i] if i < len(metas) else {}
                })
            return result
        except Exception as e:
            print(f"   [!] Memory DB Error: {e}")
            return []

    def get_random(self, n: int = 1) -> List[str]:
        data = self.collection.get(include=['documents'])
        docs = data.get('documents')
        if docs is None: docs = []
        
        if len(docs) == 0: return []
        
        import random
        if len(docs) <= n:
            return docs
        return random.sample(docs, n)

    def get_random_logs(self, n: int = 1) -> List[str]:
        """Fetch random Log Entries."""
        try:
            data = self.collection.get(
                where={"source": "log_entry"},
                include=['documents']
            )
            docs = data.get('documents')
            if not docs: return []
            
            import random
            if len(docs) <= n:
                return docs
            return random.sample(docs, n)
        except Exception as e:
            print(f"   [!] Random Logs Error: {e}")
            return []

    def get_all_embeddings(self) -> Dict[str, Any]:
        """Fetch all data including embeddings for graph visualization."""
        try:
            data = self.collection.get(include=['embeddings', 'metadatas', 'documents'])
            
            embeddings = data.get('embeddings')
            emb_count = len(embeddings) if embeddings is not None else 0
            
            ids = data.get('ids')
            id_count = len(ids) if ids is not None else 0
            
            print(f"   [MemoryDB] Fetched {id_count} IDs and {emb_count} Embeddings from DB.")
            return data
        except Exception as e:
            print(f"   [!] Memory DB Graph Error: {e}")
            return {}

    def delete(self, mem_id: str) -> None:
        self.collection.delete(ids=[mem_id])
        print(f"   [-] Memory Deleted: {mem_id}")

    def recall_by_vector(self, vector: List[float], n: int = 2, where: Optional[Dict[str, Any]] = None) -> List[str]:
        try:
            results = self.collection.query(
                query_embeddings=[vector],
                n_results=n,
                where=where
            )
            # Chroma returns list of lists (one per query)
            docs = results.get('documents')
            if docs and len(docs) > 0:
                return docs[0]
            return []
        except Exception as e:
            print(f"   [!] Memory Recall Error: {e}")
            return []

    def recall_structured(self, vector: List[float], n_logs: int = 1, n_facts: int = 5, username: Optional[str] = None) -> Dict[str, List[str]]:
        """
        Retrieves memories separated by type:
        - Log Entries (source='log_entry')
        - Facts (source='strict_fact') filtered by user if provided.
        """
        data = {"log_entries": [], "facts": []}
        try:
            # 1. Fetch Log Entries (The Narrative Context) - Generally global/system
            logs = self.collection.query(
                query_embeddings=[vector],
                n_results=n_logs,
                where={"source": "log_entry"}
            )
            if logs['documents'] and len(logs['documents']) > 0:
                data["log_entries"] = logs['documents'][0]

            # 2. Fetch Facts (strict_fact)
            # If username is provided, we filter for that user OR system facts
            fact_where: Dict[str, Any] = {"source": "strict_fact"}
            if username:
                # Resolve aliases for the filter
                search_terms = [username, "system"]
                from services.alias_manager import AliasManager
                alias_map = AliasManager.load_aliases()
                target_handle = username.replace("@", "")
                reverse_aliases = [k for k, v in alias_map.items() if v.replace("@", "") == target_handle]
                search_terms.extend(reverse_aliases)
                if target_handle in alias_map:
                    search_terms.append(alias_map[target_handle])
                search_terms = list(set(search_terms))
                
                fact_where = {
                    "$and": [
                        {"source": "strict_fact"},
                        {"user": {"$in": search_terms}}
                    ]
                }

            facts = self.collection.query(
                query_embeddings=[vector],
                n_results=n_facts,
                where=fact_where
            )
            if facts['documents'] and len(facts['documents']) > 0:
                data["facts"] = facts['documents'][0]
            
            return data

        except Exception as e:
            print(f"   [!] Structured Recall Error: {e}")
            return data

    def get_facts_by_user(self, username: str, limit: int = 10) -> List[str]:
        """Fetch facts strictly about a specific user (including their aliases)."""
        import json
        from services.alias_manager import AliasManager
        
        # 1. Resolve Aliases
        search_terms = [username]
        alias_map = AliasManager.load_aliases()
        
        # Find all aliases that map to this username (if it's a handle) OR if username is an alias
        target_handle = username.replace("@", "")
        
        # Case A: aliases that point to this user
        reverse_aliases = [k for k, v in alias_map.items() if v.replace("@", "") == target_handle]
        search_terms.extend(reverse_aliases)
        
        # Case B: if input was an alias, get the real handle
        if target_handle in alias_map:
             search_terms.append(alias_map[target_handle])
            
        search_terms = list(set(search_terms)) # Dedupe
        
        # 2. Query DB (Chroma 'where' clause using $in operator if supported, else loop)
        # Chroma's 'where' operator "$in" is supported in newer versions.
        # Format: "where": {"user": {"$in": ["alice", "bob"]}}
        
        try:
            results = self.collection.get(
                where={"user": {"$in": search_terms}},
                limit=limit
            )
            return results.get("documents", [])
        except Exception as e:
            print(f"   [!] Fact Fetch Error for {username}: {e}")
            return []
