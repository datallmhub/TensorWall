'use client';

import { useState, useRef, useEffect } from 'react';
import { Send, Settings, Trash2, Copy, Check, Loader2, RefreshCw, Download, AlertCircle } from 'lucide-react';
import { api } from '@/lib/api';

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  tokens?: number;
  latency?: number;
  model?: string;
}

interface ModelInfo {
  id: string;
  name: string;
  provider: string;
  description?: string;
  available: boolean;
}

interface ProviderStatus {
  name: string;
  available: boolean;
  base_url?: string;
  model_count: number;
}

export default function PlaygroundPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const [availableModels, setAvailableModels] = useState<ModelInfo[]>([]);
  const [providers, setProviders] = useState<ProviderStatus[]>([]);
  const [loadingModels, setLoadingModels] = useState(false);
  const [modelsError, setModelsError] = useState<string | null>(null);
  const [discoveringProvider, setDiscoveringProvider] = useState<string | null>(null);

  const [settings, setSettings] = useState({
    model: 'mock-gpt',
    apiKey: 'gw_test_key_123',
    llmApiKey: '',
    temperature: 0.7,
    maxTokens: 1000,
    systemPrompt: 'You are a helpful assistant.',
  });

  // Load available models on mount
  useEffect(() => {
    loadModels();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadModels = async () => {
    setLoadingModels(true);
    setModelsError(null);
    try {
      const data = await api.getModels();
      setAvailableModels(data.models || []);
      setProviders(data.providers || []);

      // If no models and current model not in list, keep mock-gpt as default
      if (data.models && data.models.length > 0) {
        const modelExists = data.models.some((m: ModelInfo) => m.id === settings.model);
        if (!modelExists) {
          // Select first available model
          setSettings(s => ({ ...s, model: data.models[0].id }));
        }
      }
    } catch (error) {
      console.error('Failed to load models:', error);
      setModelsError(error instanceof Error ? error.message : 'Cannot connect to backend. Is the server running?');
      // Fallback to mock model only
      setAvailableModels([
        { id: 'mock-gpt', name: 'Mock GPT (Testing)', provider: 'mock', available: true },
      ]);
    } finally {
      setLoadingModels(false);
    }
  };

  const discoverModels = async (provider: 'ollama' | 'lmstudio') => {
    setDiscoveringProvider(provider);
    try {
      const data = await api.discoverModels(provider);
      // Reload models after discovery
      await loadModels();
      alert(`${data.message}`);
    } catch (error) {
      alert(error instanceof Error ? error.message : `Failed to discover ${provider} models. Is ${provider} running?`);
    } finally {
      setDiscoveringProvider(null);
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    const startTime = Date.now();

    try {
      const requestMessages = [
        ...(settings.systemPrompt ? [{ role: 'system', content: settings.systemPrompt }] : []),
        ...messages.map((m) => ({ role: m.role, content: m.content })),
        { role: 'user', content: userMessage.content },
      ];

      const data = await api.chat(settings.model, requestMessages, {
        gatewayApiKey: settings.apiKey,
        llmApiKey: settings.llmApiKey || undefined,
        temperature: settings.temperature,
        maxTokens: settings.maxTokens,
      });

      const latency = Date.now() - startTime;

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: data.choices[0].message.content,
        timestamp: new Date(),
        tokens: data.usage?.total_tokens,
        latency,
        model: data.model,
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `Error: ${error instanceof Error ? error.message : 'Unknown error'}`,
        timestamp: new Date(),
        latency: Date.now() - startTime,
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const copyToClipboard = (content: string, id: string) => {
    navigator.clipboard.writeText(content);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const clearChat = () => {
    setMessages([]);
  };

  // Check if local providers are available
  const ollamaProvider = providers.find(p => p.name === 'ollama');
  const lmstudioProvider = providers.find(p => p.name === 'lmstudio');

  return (
    <div className="h-[calc(100vh-8rem)] flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Playground</h1>
          <p className="text-gray-500 mt-1">Test LLM requests through the gateway</p>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={clearChat}
            className="flex items-center px-3 py-2 text-gray-600 hover:bg-gray-100 rounded-lg"
          >
            <Trash2 className="w-4 h-4 mr-2" />
            Clear
          </button>
          <button
            onClick={() => setShowSettings(!showSettings)}
            className={`flex items-center px-3 py-2 rounded-lg ${showSettings ? 'bg-blue-100 text-blue-600' : 'text-gray-600 hover:bg-gray-100'}`}
          >
            <Settings className="w-4 h-4 mr-2" />
            Settings
          </button>
        </div>
      </div>

      <div className="flex-1 flex gap-4 min-h-0">
        {/* Chat Area */}
        <div className="flex-1 flex flex-col bg-white rounded-xl shadow-sm overflow-hidden">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.length === 0 && (
              <div className="h-full flex items-center justify-center text-gray-400">
                <div className="text-center">
                  <p className="text-lg mb-2">Start a conversation</p>
                  <p className="text-sm">Your messages will be sent through TensorWall</p>
                  {modelsError && (
                    <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg text-yellow-700 text-sm">
                      <AlertCircle className="w-4 h-4 inline mr-2" />
                      {modelsError}
                    </div>
                  )}
                </div>
              </div>
            )}
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[80%] rounded-xl px-4 py-3 ${
                    message.role === 'user'
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 text-gray-900'
                  }`}
                >
                  <div className="whitespace-pre-wrap">{message.content}</div>
                  <div className={`flex items-center justify-between mt-2 text-xs ${message.role === 'user' ? 'text-blue-200' : 'text-gray-400'}`}>
                    <span>{message.timestamp.toLocaleTimeString()}</span>
                    <div className="flex items-center space-x-3">
                      {message.tokens && <span>{message.tokens} tokens</span>}
                      {message.latency && <span>{message.latency}ms</span>}
                      {message.model && <span>{message.model}</span>}
                      <button
                        onClick={() => copyToClipboard(message.content, message.id)}
                        className="hover:opacity-70"
                      >
                        {copiedId === message.id ? (
                          <Check className="w-3 h-3" />
                        ) : (
                          <Copy className="w-3 h-3" />
                        )}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-gray-100 rounded-xl px-4 py-3">
                  <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <form onSubmit={handleSubmit} className="border-t p-4">
            <div className="flex items-center space-x-3">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Type your message..."
                className="flex-1 px-4 py-3 border rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                disabled={isLoading}
              />
              <button
                type="submit"
                disabled={isLoading || !input.trim()}
                className="px-4 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Send className="w-5 h-5" />
              </button>
            </div>
          </form>
        </div>

        {/* Settings Panel */}
        {showSettings && (
          <div className="w-80 bg-white rounded-xl shadow-sm p-6 overflow-y-auto">
            <h3 className="font-semibold text-gray-900 mb-4">Request Settings</h3>
            <div className="space-y-4">
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="block text-sm font-medium text-gray-700">
                    Model
                  </label>
                  <button
                    onClick={loadModels}
                    disabled={loadingModels}
                    className="text-blue-600 hover:text-blue-800 text-sm flex items-center"
                    title="Refresh models"
                  >
                    <RefreshCw className={`w-3 h-3 mr-1 ${loadingModels ? 'animate-spin' : ''}`} />
                    Refresh
                  </button>
                </div>
                <select
                  value={settings.model}
                  onChange={(e) => setSettings({ ...settings, model: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                  disabled={loadingModels}
                >
                  {availableModels.length === 0 ? (
                    <option value="">No models available</option>
                  ) : (
                    /* Group models by provider */
                    Array.from(new Set(availableModels.map((m) => m.provider))).map((provider) => {
                      const providerModels = availableModels.filter((m) => m.provider === provider);
                      if (providerModels.length === 0) return null;
                      const providerStatus = providers.find((p) => p.name === provider);
                      const providerLabel = provider.charAt(0).toUpperCase() + provider.slice(1).replace('_', ' ');
                      return (
                        <optgroup
                          key={provider}
                          label={`${providerLabel}${providerStatus?.available === false ? ' (Offline)' : ''}`}
                        >
                          {providerModels.map((model) => (
                            <option key={model.id} value={model.id}>
                              {model.name}
                            </option>
                          ))}
                        </optgroup>
                      );
                    })
                  )}
                </select>

                {/* Local providers discovery */}
                <div className="mt-3 space-y-2">
                  <p className="text-xs text-gray-500 font-medium">Discover Local Models:</p>
                  <div className="flex gap-2">
                    <button
                      onClick={() => discoverModels('ollama')}
                      disabled={discoveringProvider !== null}
                      className={`flex-1 px-2 py-1.5 text-xs rounded-lg flex items-center justify-center gap-1 ${
                        ollamaProvider?.available
                          ? 'bg-green-100 text-green-700 hover:bg-green-200'
                          : 'bg-gray-100 text-gray-500'
                      }`}
                      title={ollamaProvider?.available ? 'Ollama is running' : 'Ollama is offline'}
                    >
                      {discoveringProvider === 'ollama' ? (
                        <Loader2 className="w-3 h-3 animate-spin" />
                      ) : (
                        <Download className="w-3 h-3" />
                      )}
                      Ollama
                      {ollamaProvider?.available && <span className="w-1.5 h-1.5 bg-green-500 rounded-full"></span>}
                    </button>
                    <button
                      onClick={() => discoverModels('lmstudio')}
                      disabled={discoveringProvider !== null}
                      className={`flex-1 px-2 py-1.5 text-xs rounded-lg flex items-center justify-center gap-1 ${
                        lmstudioProvider?.available
                          ? 'bg-green-100 text-green-700 hover:bg-green-200'
                          : 'bg-gray-100 text-gray-500'
                      }`}
                      title={lmstudioProvider?.available ? 'LM Studio is running' : 'LM Studio is offline'}
                    >
                      {discoveringProvider === 'lmstudio' ? (
                        <Loader2 className="w-3 h-3 animate-spin" />
                      ) : (
                        <Download className="w-3 h-3" />
                      )}
                      LM Studio
                      {lmstudioProvider?.available && <span className="w-1.5 h-1.5 bg-green-500 rounded-full"></span>}
                    </button>
                  </div>
                  <p className="text-xs text-gray-400">
                    Click to import models from local providers
                  </p>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Gateway API Key
                </label>
                <input
                  type="text"
                  value={settings.apiKey}
                  onChange={(e) => setSettings({ ...settings, apiKey: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 font-mono text-sm"
                  placeholder="gw_..."
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  LLM API Key (OpenAI/Anthropic)
                </label>
                <input
                  type="password"
                  value={settings.llmApiKey}
                  onChange={(e) => setSettings({ ...settings, llmApiKey: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 font-mono text-sm"
                  placeholder="sk-... or sk-ant-..."
                />
                <p className="text-xs text-gray-500 mt-1">
                  Leave empty for mock/local models
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Temperature: {settings.temperature}
                </label>
                <input
                  type="range"
                  min="0"
                  max="2"
                  step="0.1"
                  value={settings.temperature}
                  onChange={(e) => setSettings({ ...settings, temperature: parseFloat(e.target.value) })}
                  className="w-full"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Max Tokens
                </label>
                <input
                  type="number"
                  value={settings.maxTokens}
                  onChange={(e) => setSettings({ ...settings, maxTokens: parseInt(e.target.value) })}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                  min={1}
                  max={4096}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  System Prompt
                </label>
                <textarea
                  value={settings.systemPrompt}
                  onChange={(e) => setSettings({ ...settings, systemPrompt: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 h-24 resize-none"
                  placeholder="You are a helpful assistant..."
                />
              </div>
            </div>

            <div className="mt-6 p-4 bg-gray-50 rounded-lg">
              <h4 className="text-sm font-medium text-gray-700 mb-2">Request Info</h4>
              <div className="text-xs text-gray-500 space-y-1">
                <p>Endpoint: <code className="bg-blue-100 text-blue-700 px-1 rounded">/v1/chat/completions</code></p>
                <p>Selected: <code className="bg-gray-200 text-gray-700 px-1 rounded">{settings.model}</code></p>
                <p>Headers:</p>
                <ul className="list-disc list-inside ml-2">
                  <li>X-API-Key: Gateway auth</li>
                  <li>Authorization: Bearer (LLM key)</li>
                </ul>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
