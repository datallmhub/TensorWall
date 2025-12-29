'use client';

import { Search, Home, ArrowLeft } from 'lucide-react';
import Link from 'next/link';

export default function NotFound() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-50 flex items-center justify-center p-4">
      <div className="max-w-2xl w-full">
        {/* 404 Icon */}
        <div className="flex justify-center mb-6">
          <div className="bg-blue-100 p-6 rounded-full">
            <Search className="w-16 h-16 text-blue-600" />
          </div>
        </div>

        {/* 404 Message */}
        <div className="bg-white rounded-2xl shadow-xl p-8 text-center">
          <h1 className="text-6xl font-bold text-blue-600 mb-4">404</h1>
          <h2 className="text-3xl font-bold text-gray-900 mb-4">
            Page introuvable
          </h2>
          <p className="text-gray-600 mb-8">
            Désolé, la page que vous recherchez n&apos;existe pas ou a été déplacée.
          </p>

          {/* Actions */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <button
              onClick={() => window.history.back()}
              className="flex items-center justify-center gap-2 px-6 py-3 border-2 border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors font-medium"
            >
              <ArrowLeft className="w-5 h-5" />
              Retour
            </button>
            <Link
              href="/"
              className="flex items-center justify-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
            >
              <Home className="w-5 h-5" />
              Retour à l&apos;accueil
            </Link>
          </div>

          {/* Quick Links */}
          <div className="mt-8 pt-6 border-t border-gray-200">
            <p className="text-sm text-gray-600 mb-4">Liens utiles :</p>
            <div className="flex flex-wrap justify-center gap-4">
              <Link href="/applications" className="text-blue-600 hover:underline text-sm">
                Applications
              </Link>
              <Link href="/budgets" className="text-blue-600 hover:underline text-sm">
                Budgets
              </Link>
              <Link href="/policies" className="text-blue-600 hover:underline text-sm">
                Policies
              </Link>
              <Link href="/analytics" className="text-blue-600 hover:underline text-sm">
                Analytics
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
