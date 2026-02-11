import React, { useEffect, useState, useRef } from 'react';
import { Send, Image, Heart, MoreHorizontal, Phone, Video } from 'lucide-react';
import { api, socket } from '../services/api';
import clsx from 'clsx';

const ChatBubble = ({ msg }) => {
  const isMe = msg.sender === 'Fern' || msg.sender.toLowerCase().includes('you');
  return (
    <div className={clsx("flex gap-2 max-w-[70%]", isMe ? "self-end flex-row-reverse" : "self-start")}>
      {!isMe && (
        <div className="w-7 h-7 rounded-full bg-gray-200 flex-shrink-0 overflow-hidden">
           <img 
             src={`https://ui-avatars.com/api/?name=${msg.sender}&background=random&color=fff&size=28`} 
             alt={msg.sender} 
           />
        </div>
      )}
      
      <div className={clsx(
        "px-4 py-2 rounded-2xl text-sm leading-relaxed",
        isMe 
          ? "bg-[#efefef] text-black" // Instagram Web uses gray for own messages strangely, or blue. Let's use Blue for clarity or Gray style. 
          // Actually Insta Web: Me = Gray (efefef), Them = White (border) or Transparent? 
          // Let's go with Standard Messenger: Me = Blue, Them = Gray.
          : "border border-border bg-white text-text"
      )}>
         {isMe && <div className={clsx("bg-primary text-white px-4 py-2 rounded-2xl")}>{msg.text}</div>}
         {!isMe && <div>{msg.text}</div>}
      </div>
      
      {/* Correction: Insta style */}
    </div>
  );
};

// Fixed Bubble Style for 'Real' Look
const Message = ({ msg }) => {
   const isMe = msg.sender === 'Fern' || msg.sender.toLowerCase().includes('you');
   return (
      <div className={clsx("flex w-full mb-1", isMe ? "justify-end" : "justify-start")}>
         <div className={clsx(
            "max-w-[65%] px-4 py-3 text-[15px] leading-snug break-words",
            isMe 
              ? "bg-[#3797f0] text-white rounded-[22px] rounded-br-[4px]" 
              : "bg-[#efefef] text-black rounded-[22px] rounded-bl-[4px]"
         )}>
            {msg.text}
         </div>
      </div>
   );
};

export default function Chat() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const scrollRef = useRef(null);

  useEffect(() => {
    const unsub = socket.subscribe((data) => {
      if (data.type === 'chat_message') {
        setMessages(prev => [...prev, { sender: data.sender, text: data.text, id: Date.now() }]);
      }
    });
    return () => unsub();
  }, []);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;
    
    // Optimistic UI
    const text = input;
    setInput("");
    setMessages(prev => [...prev, { sender: "You", text: text, id: Date.now() }]);

    const payload = text.startsWith('/') ? { text } : { text: `/say ${text}` };
    await api.post('/command', payload);
  };

  return (
    <div className="card h-[calc(100vh-140px)] md:h-[calc(100vh-100px)] flex flex-col overflow-hidden border-border bg-surface shadow-sm">
      
      {/* Chat Header */}
      <div className="h-16 border-b border-border flex items-center justify-between px-6 bg-white">
         <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-gray-200 overflow-hidden">
               <img src="https://ui-avatars.com/api/?name=Current+Chat" alt="" />
            </div>
            <div className="font-semibold text-text">Live Thread</div>
         </div>
         <div className="flex gap-4 text-text">
            <Phone size={24} strokeWidth={1.5} />
            <Video size={24} strokeWidth={1.5} />
            <MoreHorizontal size={24} strokeWidth={1.5} />
         </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-5 space-y-2 bg-white" ref={scrollRef}>
        {messages.length === 0 && (
           <div className="h-full flex flex-col items-center justify-center text-center">
              <div className="w-24 h-24 rounded-full border-2 border-text mb-4 flex items-center justify-center">
                 <Send size={48} strokeWidth={1} />
              </div>
              <h3 className="text-xl font-light mb-1">Your Messages</h3>
              <p className="text-text-secondary text-sm">Send a message to start a chat.</p>
           </div>
        )}
        
        {/* Timestamp Separator Example */}
        {messages.length > 0 && (
           <div className="text-center text-xs text-text-tertiary font-semibold my-4">TODAY</div>
        )}

        {messages.map((m, i) => (
          <Message key={m.id || i} msg={m} />
        ))}
      </div>

      {/* Input Area */}
      <div className="p-4 bg-white">
         <form onSubmit={sendMessage} className="border border-border rounded-[22px] px-4 py-2 flex items-center gap-3 bg-white focus-within:ring-1 focus-within:ring-border">
            <div className="p-1 cursor-pointer hover:bg-gray-100 rounded-full transition-colors">
               <div className="text-text font-bold text-xl leading-none pb-1">☺</div>
            </div>
            <input 
              type="text" 
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Message..."
              className="flex-1 text-sm bg-transparent outline-none placeholder:text-text-secondary h-8"
            />
            {input.trim() ? (
               <button type="submit" className="text-primary font-semibold text-sm hover:text-primary-hover">Send</button>
            ) : (
               <>
                  <Image size={24} className="text-text cursor-pointer hover:text-text-secondary" strokeWidth={1.5} />
                  <Heart size={24} className="text-text cursor-pointer hover:text-text-secondary" strokeWidth={1.5} />
               </>
            )}
         </form>
      </div>

    </div>
  );
}