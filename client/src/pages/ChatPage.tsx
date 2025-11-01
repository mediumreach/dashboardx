import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { Send, Loader2 } from 'lucide-react';
import { queryClient, apiRequest } from '@/lib/queryClient';
import { getDemoConfig } from '@/lib/demoConfig';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  createdAt: string;
}

export function ChatPage() {
  const [input, setInput] = useState('');

  const { data: config } = useQuery({
    queryKey: ['/api/demo/config'],
    queryFn: getDemoConfig,
  });

  const { data: messages = [], isLoading } = useQuery<Message[]>({
    queryKey: ['/api/chat/sessions', config?.sessionId, 'messages'],
    queryFn: async () => {
      if (!config) return [];
      const res = await fetch(`/api/chat/sessions/${config.sessionId}/messages`);
      if (!res.ok) return [];
      return res.json();
    },
    enabled: !!config,
  });

  const sendMessage = useMutation({
    mutationFn: async (content: string) => {
      if (!config) throw new Error('Config not loaded');
      return apiRequest(`/api/chat/messages`, {
        method: 'POST',
        body: JSON.stringify({
          sessionId: config.sessionId,
          tenantId: config.tenantId,
          role: 'user',
          content,
          metadata: {},
        }),
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/api/chat/sessions', config?.sessionId, 'messages'] });
      setInput('');
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || sendMessage.isPending) return;
    sendMessage.mutate(input);
  };

  return (
    <div className="max-w-5xl mx-auto h-[calc(100vh-8rem)] flex flex-col">
      <div className="mb-6 animate-fade-in">
        <h1 className="text-4xl font-bold bg-gradient-to-r from-cyan-600 to-blue-600 bg-clip-text text-transparent mb-2" data-testid="text-page-title">AI Chat</h1>
        <p className="text-gray-600">Ask questions about your documents using RAG-powered AI</p>
      </div>

      <div className="flex-1 bg-white/80 backdrop-blur-xl rounded-2xl border border-gray-200/50 shadow-xl overflow-y-auto p-6 space-y-4 mb-4 custom-scrollbar">
        {isLoading ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <div className="w-16 h-16 border-4 border-cyan-200 border-t-cyan-600 rounded-full animate-spin mx-auto mb-4"></div>
              <p className="text-gray-600 font-medium">Loading messages...</p>
            </div>
          </div>
        ) : messages.length === 0 ? (
          <div className="flex items-center justify-center h-full text-gray-500" data-testid="text-empty-state">
            <div className="text-center animate-fade-in">
              <div className="w-20 h-20 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-lg">
                <Send className="w-10 h-10 text-white" />
              </div>
              <p className="text-xl font-semibold text-gray-700 mb-2">No messages yet</p>
              <p className="text-sm text-gray-500">Start a conversation by typing below</p>
            </div>
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'} animate-fade-in-up`}
              data-testid={`message-${message.id}`}
            >
              <div
                className={`max-w-[75%] rounded-2xl px-5 py-3 shadow-md ${
                  message.role === 'user'
                    ? 'bg-gradient-to-r from-cyan-600 to-blue-600 text-white'
                    : 'bg-white border border-gray-200'
                }`}
              >
                <p className={`text-sm whitespace-pre-wrap leading-relaxed ${
                  message.role === 'user' ? 'text-white' : 'text-gray-800'
                }`}>{message.content}</p>
                <p className={`text-xs mt-2 ${
                  message.role === 'user' ? 'text-cyan-100' : 'text-gray-500'
                }`}>
                  {new Date(message.createdAt).toLocaleTimeString()}
                </p>
              </div>
            </div>
          ))
        )}
      </div>

      <form onSubmit={handleSubmit} className="flex gap-3 animate-fade-in">
        <div className="flex-1 relative">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a question about your documents..."
            className="w-full px-6 py-4 bg-white/80 backdrop-blur-xl border-2 border-gray-200 rounded-2xl focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent shadow-lg hover:shadow-xl transition-all duration-300 placeholder-gray-400"
            disabled={sendMessage.isPending}
            data-testid="input-message"
          />
        </div>
        <button
          type="submit"
          disabled={!input.trim() || sendMessage.isPending}
          className="px-8 py-4 bg-gradient-to-r from-cyan-600 to-blue-600 text-white rounded-2xl hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 transition-all duration-300 hover:scale-105 active:scale-95 shadow-lg shadow-cyan-500/30 font-medium"
          data-testid="button-send"
        >
          {sendMessage.isPending ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              <span>Sending...</span>
            </>
          ) : (
            <>
              <Send className="w-5 h-5" />
              <span>Send</span>
            </>
          )}
        </button>
      </form>
    </div>
  );
}
