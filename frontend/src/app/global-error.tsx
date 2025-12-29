'use client';

import { AlertTriangle, RefreshCw } from 'lucide-react';

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html>
      <body>
        <div className="min-h-screen bg-gradient-to-br from-red-50 to-orange-50 flex items-center justify-center p-4">
          <div className="max-w-2xl w-full">
            {/* Error Icon */}
            <div className="flex justify-center mb-6">
              <div className="bg-red-100 p-6 rounded-full">
                <AlertTriangle className="w-16 h-16 text-red-600" />
              </div>
            </div>

            {/* Error Message */}
            <div className="bg-white rounded-2xl shadow-xl p-8 text-center">
              <h1 className="text-3xl font-bold text-gray-900 mb-4">
                Erreur critique
              </h1>
              <p className="text-gray-600 mb-6">
                Une erreur critique s&apos;est produite. Veuillez recharger la page ou contacter le support technique.
              </p>

              {/* Error Details (Only in development) */}
              {process.env.NODE_ENV === 'development' && (
                <div className="mb-6 p-4 bg-red-50 rounded-lg text-left">
                  <p className="text-sm font-semibold text-red-800 mb-2">Détails de l&apos;erreur (dev only):</p>
                  <code className="text-xs text-red-700 block whitespace-pre-wrap break-all">
                    {error.message}
                  </code>
                  {error.digest && (
                    <p className="text-xs text-red-600 mt-2">
                      ID d&apos;erreur: {error.digest}
                    </p>
                  )}
                </div>
              )}

              {/* Actions */}
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <button
                  onClick={reset}
                  className="flex items-center justify-center gap-2 px-6 py-3 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors font-medium"
                >
                  <RefreshCw className="w-5 h-5" />
                  Recharger l&apos;application
                </button>
              </div>

              {/* Help Text */}
              <div className="mt-8 pt-6 border-t border-gray-200">
                <p className="text-sm text-gray-500">
                  Si le problème persiste après rechargement, veuillez contacter le support technique.
                </p>
              </div>
            </div>
          </div>
        </div>
      </body>
    </html>
  );
}
