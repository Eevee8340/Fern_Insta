import time
from datetime import datetime
from typing import Dict, Any, Tuple, Optional

class Colors:
    GREEN = "\033[92m"
    BLUE = "\033[94m"
    ENDC = "\033[0m"

class MessageProcessor:
    def __init__(self, my_user_id: Optional[str], user_map: Dict[str, str]):
        self.my_user_id = my_user_id
        self.user_map = user_map
        self.last_msg_id: Optional[str] = None
        self.last_left_sender: str = "Unknown"

    def update_identity(self, my_user_id: str):
        self.my_user_id = my_user_id

    def process_node(self, msg_node: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
        """
        Returns:
            Tuple(Parsed Message Object or None, Metadata Dict)
        """
        msg_id = msg_node.get("item_id")
        if msg_id == self.last_msg_id:
            return None, {}
        
        self.last_msg_id = msg_id
        sender_id = str(msg_node.get("user_id"))

        if sender_id == self.my_user_id:
            return None, {}

        sender_display = self.user_map.get(sender_id, f"User {sender_id}")
        
        # --- IDENTITY OVERRIDE ---
        # Used to map certain users to custom display names (optional)
        # if "(@meow.eevee)" in sender_display:                                                                                                             │
        #      sender_display = "Evoli (@meow.eevee)"                                                                                                       │
        # elif sender_display == "meow.eevee":                                                                                                              │
        #      sender_display = "Evoli (@meow.eevee)" 
        # -------------------------

        ts_micro = msg_node.get("timestamp")
        try:
            ts = int(ts_micro)
            if ts > 10000000000000: ts = ts / 1000000
            elif ts > 10000000000: ts = ts / 1000
            time_str = datetime.fromtimestamp(ts).strftime('%H:%M:%S')
        except:
            time_str = str(ts_micro)

        msg_type = msg_node.get("item_type")
        content = ""
        is_placeholder = False

        if msg_type == 'text': 
            content = msg_node.get("text")
        elif msg_type == 'media': 
            content = "[Photo/Video]"
            is_placeholder = True
        elif msg_type == 'voice_media': 
            content = "[Voice Note]"
            is_placeholder = True
        elif msg_type == 'link': 
            content = "[Link]"
            is_placeholder = True
        elif msg_type == 'media_share': 
            content = "[Shared Post]"
            is_placeholder = True
        else: 
            content = f"[{msg_type}]"
            is_placeholder = True

        reply_suffix = ""
        parent_context = ""
        reply_log = ""
        
        if "replied_to_message" in msg_node:
            try:
                r_obj = msg_node.get("replied_to_message")
                if r_obj and isinstance(r_obj, dict):
                    orig_user_id = str(r_obj.get("user_id", ""))
                    if orig_user_id == self.my_user_id:
                        reply_suffix = " replied to you"
                        target_name = "YOU"
                    else:
                        target_name = self.user_map.get(orig_user_id, "someone")
                        reply_suffix = f" (replied to {target_name})"
                    
                    r_text = r_obj.get("text")
                    if not r_text:
                        r_text = f"[{r_obj.get('item_type', 'media')}]"
                    
                    parent_context = f"Replying to {target_name}: \"{r_text}\""
                    reply_log = f"\n  {Colors.BLUE}└── Replying to {target_name}: \"{r_text}\"{Colors.ENDC}"
            except Exception as e:
                print(f"   [!] Context Parse Error: {e}")

        sender_full = sender_display + reply_suffix
        self.last_left_sender = sender_full
        
        # Construct Standard Message Object
        msg_obj = {
            "type": "chat_message",
            "sender": sender_full,
            "text": content,
            "timestamp": time.time(),
            "display_time": time_str,
            "is_placeholder": is_placeholder,
            "reply_log": reply_log
        }
        
        metadata = {
            "parent_context": parent_context,
            "reply_log": reply_log
        }

        return msg_obj, metadata
