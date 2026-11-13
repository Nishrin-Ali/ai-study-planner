import React, { useState, useEffect, useRef } from 'react';
import { X, Send, Bot, User, Sparkles, Loader2, BookOpen } from 'lucide-react';
import DOMPurify from 'dompurify';

export interface ChatMessage {
  role: 'user' | 'model';
  text: string;
  source_attribution?: string;
  grounded?: boolean;
}

interface Props {
  isOpen: boolean;
  onClose: () => void;
  planId: string;
  itemId?: string | null;
  questionText: string;
  module?: number | null;
  courseCode?: string;
}

const STARTER_PROMPTS = [
  'Explain simply',
  'Give an example',
  'Make it a 5-mark answer',
  'Quiz me on this',
];

export const StudyBuddyDrawer: React.FC<Props> = ({
  isOpen,
  onClose,
  planId,
  itemId,
  questionText,
  module,
  courseCode,
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const storageKey = `chat_history_${planId}_${itemId || questionText.slice(0, 24)}`;

  // Load chat history from localStorage
  useEffect(() => {
    if (!isOpen) return;
    try {
      const saved = localStorage.getItem(storageKey);
      if (saved) {
        setMessages(JSON.parse(saved));
      } else {
        // Welcome message from Study Buddy
        setMessages([
          {
            role: 'model',
            text: `Hey! I'm your VTU Study Buddy. Ask me anything about "${questionText}", or pick a starter prompt below and I'll break it down senior-to-junior style!`,
            grounded: true,
          },
        ]);
      }
    } catch {
      // Ignore localStorage read errors
    }
  }, [isOpen, storageKey, questionText]);

  // Persist messages to localStorage
  useEffect(() => {
    if (messages.length > 0) {
      try {
        localStorage.setItem(storageKey, JSON.stringify(messages));
      } catch {
        // Ignore localStorage write errors
      }
    }
  }, [messages, storageKey]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  if (!isOpen) return null;

  const sendMessage = async (userText: string) => {
    if (!userText.trim() || isLoading) return;

    const newMsg: ChatMessage = { role: 'user', text: userText };
    const updatedMessages = [...messages, newMsg];
    setMessages(updatedMessages);
    setInputValue('');
    setIsLoading(true);

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          plan_id: planId,
          item_id: itemId || null,
          question_text: questionText,
          user_message: userText,
          history: updatedMessages.slice(-8).map((m) => ({
            role: m.role,
            text: m.text,
          })),
          stream: true,
        }),
      });

      if (!res.ok) {
        throw new Error('Failed to reach Study Buddy server.');
      }

      // Check if response is SSE streaming or standard JSON
      const contentType = res.headers.get('content-type') || '';
      if (contentType.includes('text/event-stream') && res.body) {
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let assistantReply = '';
        let sourceAttribution = '';
        let isGrounded = true;

        // Add placeholder assistant message
        setMessages((prev) => [
          ...prev,
          { role: 'model', text: '', grounded: true },
        ]);

        let done = false;
        while (!done) {
          const { value, done: streamDone } = await reader.read();
          done = streamDone;
          if (value) {
            const chunk = decoder.decode(value, { stream: true });
            const lines = chunk.split('\n');
            for (const line of lines) {
              if (line.startsWith('data: ')) {
                const dataStr = line.slice(6).trim();
                if (!dataStr || dataStr === '[DONE]') continue;
                try {
                  const parsed = JSON.parse(dataStr);
                  if (parsed.delta) {
                    assistantReply += parsed.delta;
                    setMessages((prev) => {
                      const copy = [...prev];
                      copy[copy.length - 1] = {
                        role: 'model',
                        text: assistantReply,
                        source_attribution: sourceAttribution,
                        grounded: isGrounded,
                      };
                      return copy;
                    });
                  }
                  if (parsed.source_attribution) {
                    sourceAttribution = parsed.source_attribution;
                  }
                  if (typeof parsed.grounded === 'boolean') {
                    isGrounded = parsed.grounded;
                  }
                } catch {
                  // Raw text delta fallback
                  assistantReply += dataStr;
                }
              }
            }
          }
        }
      } else {
        const json = await res.json();
        setMessages((prev) => [
          ...prev,
          {
            role: 'model',
            text: json.reply || json.message || 'No reply generated.',
            source_attribution: json.source_attribution,
            grounded: json.grounded ?? true,
          },
        ]);
      }
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'model',
          text: `Oops, couldn't connect right now (${err.message || 'Error'}). Don't panic! Review the core definitions from your textbook first.`,
          grounded: false,
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(inputValue);
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-slate-900/40 backdrop-blur-xs flex justify-end">
      <div className="w-full max-w-md bg-white h-full flex flex-col shadow-2xl animate-in slide-in-from-right duration-200">
        {/* Header */}
        <div className="p-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-indigo-600 text-white flex items-center justify-center">
              <Bot className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-slate-900 flex items-center gap-1.5">
                <span>Study Buddy</span>
                <span className="text-[10px] bg-indigo-100 text-indigo-700 font-medium px-1.5 py-0.2 rounded">
                  VTU Senior AI
                </span>
              </h3>
              <p className="text-[11px] text-slate-500">Explains concepts simply, just like a senior.</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-md text-slate-400 hover:text-slate-600 hover:bg-slate-200/60 transition-colors"
            aria-label="Close Study Buddy"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Pinned Context Banner */}
        <div className="bg-indigo-50/70 border-b border-indigo-100 px-4 py-2.5 flex items-start gap-2 text-xs">
          <BookOpen className="w-4 h-4 text-indigo-600 shrink-0 mt-0.5" />
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 text-[10px] font-semibold text-indigo-800 uppercase tracking-wider">
              <span>{courseCode || 'VTU Subject'}</span>
              {module && <span>• Module {module}</span>}
            </div>
            <p className="font-medium text-slate-900 truncate mt-0.5">{questionText}</p>
          </div>
        </div>

        {/* Messages List */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {messages.map((m, idx) => (
            <div
              key={idx}
              className={`flex items-start gap-2.5 ${
                m.role === 'user' ? 'justify-end' : 'justify-start'
              }`}
            >
              {m.role === 'model' && (
                <div className="w-6 h-6 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center shrink-0 mt-1">
                  <Bot className="w-3.5 h-3.5" />
                </div>
              )}
              <div
                className={`max-w-[85%] rounded-lg p-3 text-xs leading-relaxed ${
                  m.role === 'user'
                    ? 'bg-indigo-600 text-white font-normal'
                    : 'bg-slate-100 text-slate-800 border border-slate-200'
                }`}
              >
                <div
                  className="whitespace-pre-line"
                  dangerouslySetInnerHTML={{
                    __html: DOMPurify.sanitize(m.text),
                  }}
                />
                {m.source_attribution && (
                  <div className="mt-2 pt-1.5 border-t border-slate-200/80 text-[10px] text-slate-500 font-mono">
                    Ref: {m.source_attribution}
                  </div>
                )}
              </div>
              {m.role === 'user' && (
                <div className="w-6 h-6 rounded-full bg-slate-200 text-slate-700 flex items-center justify-center shrink-0 mt-1">
                  <User className="w-3.5 h-3.5" />
                </div>
              )}
            </div>
          ))}

          {isLoading && (
            <div className="flex items-center gap-2 text-xs text-slate-500 italic">
              <Loader2 className="w-4 h-4 animate-spin text-indigo-600" />
              <span>Study Buddy is thinking...</span>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Starter Prompts */}
        <div className="px-4 py-2 border-t border-slate-100 bg-slate-50/60">
          <p className="text-[10px] font-medium text-slate-500 mb-1.5 flex items-center gap-1">
            <Sparkles className="w-3 h-3 text-indigo-500" /> Quick questions:
          </p>
          <div className="flex flex-wrap gap-1.5">
            {STARTER_PROMPTS.map((prompt) => (
              <button
                key={prompt}
                type="button"
                disabled={isLoading}
                onClick={() => sendMessage(prompt)}
                className="text-[11px] bg-white border border-slate-200 hover:border-indigo-400 hover:bg-indigo-50/50 text-slate-700 px-2.5 py-1 rounded-full transition-all"
              >
                {prompt}
              </button>
            ))}
          </div>
        </div>

        {/* Input Bar */}
        <div className="p-3 border-t border-slate-200 bg-white">
          <div className="flex items-center gap-2">
            <input
              type="text"
              placeholder="Ask anything (e.g. explain in simple words, Kannada/Hindi supported)..."
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isLoading}
              className="flex-1 bg-slate-50 border border-slate-300 rounded-md px-3 py-2 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
            <button
              type="button"
              onClick={() => sendMessage(inputValue)}
              disabled={!inputValue.trim() || isLoading}
              className="p-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-200 text-white rounded-md transition-colors shrink-0"
              aria-label="Send message"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
