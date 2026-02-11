import os
import json
from typing import Dict

class AliasManager:
    _aliases: Dict[str, str] = None
    
    @classmethod
    def load_aliases(cls, force_reload: bool = False) -> Dict[str, str]:
        if cls._aliases is not None and not force_reload:
            return cls._aliases
            
        cls._aliases = {}
        # Try to find aliases.json in root
        # Since this is in services/, root is ..
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(root, "aliases.json")
        
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    cls._aliases = json.load(f)
            except Exception as e:
                print(f"[AliasManager] Error loading aliases: {e}")
                
        return cls._aliases

    @classmethod
    def resolve(cls, handle: str) -> str:
        """
        Resolves a handle or alias to the canonical handle (without @).
        Example: 'evoli' -> 'meow.eevee'
        """
        aliases = cls.load_aliases()
        clean = handle.replace("@", "").lower()
        
        # Check if 'clean' is a key (alias)
        if clean in aliases:
            return aliases[clean].replace("@", "")
            
        return clean
