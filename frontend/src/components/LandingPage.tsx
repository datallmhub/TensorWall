'use client';

import { useState, FormEvent } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';
import {
  Shield,
  Zap,
  Eye,
  Server,
  ArrowRight,
  Github,
  Lock,
  DollarSign,
  Activity,
  Code,
  CheckCircle2,
  LogIn,
  AlertCircle,
  Loader2
} from 'lucide-react';

function LoginForm() {
  const { login } = useAuth();
  const [email, setEmail] = useState('demo@tensorwall.ai');
  const [password, setPassword] = useState('demo123');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setIsSubmitting(true);

    try {
      await login(email, password);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="bg-gray-900/80 backdrop-blur-sm rounded-2xl border border-gray-800 p-6 lg:p-8">
      <div className="text-center mb-6">
        <h2 className="text-xl font-bold text-white">Try the Demo</h2>
        <p className="text-gray-400 text-sm mt-1">No signup required</p>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-900/50 border border-red-500 rounded-lg flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
          <p className="text-red-200 text-sm">{error}</p>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="email" className="block text-sm font-medium text-gray-300 mb-1.5">
            Email
          </label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
            className="w-full px-4 py-2.5 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors text-sm"
          />
        </div>

        <div>
          <label htmlFor="password" className="block text-sm font-medium text-gray-300 mb-1.5">
            Password
          </label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="current-password"
            className="w-full px-4 py-2.5 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors text-sm"
          />
        </div>

        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-800 disabled:cursor-not-allowed rounded-lg text-white font-medium transition-colors"
        >
          {isSubmitting ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              Signing in...
            </>
          ) : (
            <>
              <LogIn className="w-5 h-5" />
              Access Demo
            </>
          )}
        </button>
      </form>

      <div className="mt-4 pt-4 border-t border-gray-800">
        <p className="text-xs text-gray-500 text-center">
          Pre-filled with demo credentials
        </p>
      </div>
    </div>
  );
}

export default function LandingPage() {
  const router = useRouter();

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      {/* Hero with Login */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-blue-950/50 via-gray-950 to-gray-950" />
        <div className="relative max-w-6xl mx-auto px-6 py-16 lg:py-24">
          <div className="grid lg:grid-cols-2 gap-12 lg:gap-16 items-center">
            {/* Left: Hero Text */}
            <div>
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-sm mb-6">
                <Shield className="w-4 h-4" />
                Open Source LLM Gateway
              </div>

              <h1 className="text-3xl lg:text-5xl font-bold tracking-tight mb-6">
                <span className="text-white">Govern access, cost and security</span>
                <br />
                <span className="text-blue-400">for any LLM</span>
              </h1>

              <p className="text-lg text-gray-400 mb-8">
                Self-hosted gateway compatible with OpenAI APIs.
                Budget control, policies, observability. Any provider. Any language.
              </p>

              <a
                href="https://github.com/datallmhub/TensorWall"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-gray-800 hover:bg-gray-700 text-white font-medium rounded-lg transition-colors border border-gray-700"
              >
                <Github className="w-5 h-5" />
                Self-host on GitHub
              </a>
            </div>

            {/* Right: Login Form */}
            <div className="lg:pl-8">
              <LoginForm />
            </div>
          </div>
        </div>
      </section>

      {/* Problem */}
      <section className="py-16 border-t border-gray-800">
        <div className="max-w-6xl mx-auto px-6">
          <h2 className="text-2xl lg:text-3xl font-bold text-center mb-4">
            Using LLMs in production is messy
          </h2>
          <p className="text-gray-400 text-center mb-10 max-w-2xl mx-auto">
            Every team reinvents the same problems. Every language duplicates the same logic.
          </p>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[
              { icon: DollarSign, text: 'No global cost control across providers' },
              { icon: Lock, text: 'Policies scattered between SDKs and clouds' },
              { icon: Eye, text: 'No audit trail for prompts and decisions' },
              { icon: Server, text: 'Vendor lock-in (OpenAI / Azure / Bedrock)' },
              { icon: Code, text: 'Every language reinvents the same logic' },
              { icon: Activity, text: 'No visibility into usage patterns' },
            ].map((item, i) => (
              <div key={i} className="flex items-start gap-3 p-4 rounded-lg bg-gray-900/50 border border-gray-800">
                <div className="p-2 rounded-lg bg-red-500/10">
                  <item.icon className="w-4 h-4 text-red-400" />
                </div>
                <p className="text-gray-300 text-sm">{item.text}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Solution */}
      <section className="py-16 border-t border-gray-800 bg-gray-900/30">
        <div className="max-w-6xl mx-auto px-6">
          <h2 className="text-2xl lg:text-3xl font-bold text-center mb-4">
            One gateway. Full control.
          </h2>
          <p className="text-gray-400 text-center mb-10 max-w-2xl mx-auto">
            Drop-in replacement for OpenAI API. Works with any provider, any language.
          </p>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[
              { icon: Zap, title: 'OpenAI-compatible API', desc: '/v1/chat/completions works out of the box' },
              { icon: DollarSign, title: 'Centralized budgets', desc: 'Per-app, per-environment cost limits' },
              { icon: Shield, title: 'Policy engine', desc: 'Control models, users, environments' },
              { icon: Eye, title: 'Full audit trail', desc: 'Every request logged and traceable' },
              { icon: Activity, title: 'Real-time observability', desc: 'Latency, tokens, costs in one place' },
              { icon: Lock, title: 'Self-hosted', desc: 'No data leaves your infrastructure' },
            ].map((item, i) => (
              <div key={i} className="p-5 rounded-xl bg-gray-900 border border-gray-800 hover:border-gray-700 transition-colors">
                <div className="p-2.5 rounded-lg bg-blue-500/10 w-fit mb-3">
                  <item.icon className="w-5 h-5 text-blue-400" />
                </div>
                <h3 className="font-semibold text-white mb-1">{item.title}</h3>
                <p className="text-gray-400 text-sm">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="py-16 border-t border-gray-800">
        <div className="max-w-4xl mx-auto px-6">
          <h2 className="text-2xl lg:text-3xl font-bold text-center mb-10">
            How it works
          </h2>

          <div className="relative">
            <div className="flex flex-col items-center gap-3">
              <div className="px-5 py-3 rounded-lg bg-gray-800 border border-gray-700 text-center">
                <Code className="w-5 h-5 text-gray-400 mx-auto mb-1" />
                <p className="font-mono text-sm text-gray-300">Your App (any language)</p>
              </div>

              <div className="w-px h-6 bg-gray-700" />
              <ArrowRight className="w-4 h-4 text-gray-500 rotate-90" />
              <div className="w-px h-6 bg-gray-700" />

              <div className="px-6 py-5 rounded-xl bg-blue-600/20 border-2 border-blue-500/50 text-center">
                <Shield className="w-7 h-7 text-blue-400 mx-auto mb-2" />
                <p className="font-bold text-blue-300">TensorWall Gateway</p>
                <p className="text-xs text-blue-400/70 mt-1">Policies • Budgets • Audit</p>
              </div>

              <div className="w-px h-6 bg-gray-700" />
              <ArrowRight className="w-4 h-4 text-gray-500 rotate-90" />
              <div className="w-px h-6 bg-gray-700" />

              <div className="flex flex-wrap justify-center gap-3">
                {['OpenAI', 'Claude', 'Ollama', 'Bedrock'].map((provider) => (
                  <div key={provider} className="px-3 py-1.5 rounded-lg bg-gray-800 border border-gray-700">
                    <p className="font-mono text-sm text-gray-400">{provider}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="mt-8 text-center">
              <p className="text-gray-400 text-sm">
                Your app talks HTTP. The gateway enforces governance. Providers stay replaceable.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* OSS */}
      <section className="py-16 border-t border-gray-800 bg-gray-900/30">
        <div className="max-w-4xl mx-auto px-6">
          <div className="p-8 rounded-xl bg-gray-900 border border-gray-800 text-center">
            <div className="inline-flex items-center justify-center p-3 rounded-lg bg-gray-800 mb-4">
              <Github className="w-8 h-8 text-white" />
            </div>
            <h2 className="text-2xl font-bold mb-2">100% Open Source</h2>
            <p className="text-gray-400 mb-6">Apache 2.0 License. Deploy anywhere. No vendor lock-in.</p>

            <div className="flex flex-wrap justify-center gap-4 mb-8">
              {[
                'Docker install in minutes',
                'Local or on-prem deployment',
                'Full API compatibility',
              ].map((item, i) => (
                <div key={i} className="flex items-center gap-2 text-gray-300 text-sm">
                  <CheckCircle2 className="w-4 h-4 text-green-500" />
                  {item}
                </div>
              ))}
            </div>

            <a
              href="https://github.com/datallmhub/TensorWall"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-gray-800 hover:bg-gray-700 text-white font-medium rounded-lg transition-colors border border-gray-700"
            >
              <Github className="w-5 h-5" />
              View on GitHub
            </a>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-6 border-t border-gray-800">
        <div className="max-w-6xl mx-auto px-6">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <Shield className="w-5 h-5 text-blue-500" />
              <span className="font-semibold">TensorWall</span>
            </div>
            <p className="text-sm text-gray-500">
              Open source LLM gateway. Apache 2.0 License.
            </p>
            <a
              href="https://github.com/datallmhub/TensorWall"
              target="_blank"
              rel="noopener noreferrer"
              className="text-gray-400 hover:text-white transition-colors"
            >
              <Github className="w-5 h-5" />
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
