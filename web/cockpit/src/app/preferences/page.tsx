'use client';

/**
 * Email Preferences Page (Phase 6)
 *
 * Features:
 * - NLP Chat Interface for natural language preference input
 * - Active Rules List with management
 * - Real-time intent parsing feedback
 * - Confirmation workflow for parsed intents
 */

import { useState } from 'react';
import { Send, Loader2, CheckCircle2, XCircle, AlertCircle } from 'lucide-react';

interface ParsedIntent {
  intent_type: string;
  sender_email?: string;
  sender_domain?: string;
  sender_name?: string;
  trust_level?: string;
  categories: string[];
  preferred_primary_category?: string;
  confidence: number;
  reasoning: string;
  key_signals: string[];
  original_text: string;
}

interface IntentParserResult {
  parsed_intent: ParsedIntent;
  suggested_actions: string[];
  requires_confirmation: boolean;
}

interface UserPreferenceRule {
  id: number;
  rule_id: string;
  account_id: string;
  pattern: string;
  action: string;
  active: boolean;
  created_at: string;
  created_via: string;
}

export default function PreferencesPage() {
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [parseResult, setParseResult] = useState<IntentParserResult | null>(null);
  const [executeResult, setExecuteResult] = useState<{ success: boolean; message: string } | null>(null);
  const [rules, setRules] = useState<UserPreferenceRule[]>([]);
  const [showRules, setShowRules] = useState(true);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!inputText.trim()) return;

    setIsLoading(true);
    setParseResult(null);
    setExecuteResult(null);

    try {
      // Call NLP Intent Parser API
      const response = await fetch('/api/preferences/parse', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: inputText,
          account_id: 'gmail_1' // TODO: Get from user context
        })
      });

      if (!response.ok) {
        throw new Error('Failed to parse intent');
      }

      const result: IntentParserResult = await response.json();
      setParseResult(result);

    } catch (error) {
      console.error('Error parsing intent:', error);
      setExecuteResult({
        success: false,
        message: 'Fehler beim Parsen der Eingabe. Bitte versuche es erneut.'
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleConfirm = async () => {
    if (!parseResult) return;

    setIsLoading(true);

    try {
      // Execute parsed intent
      const response = await fetch('/api/preferences/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          parsed_intent: parseResult.parsed_intent,
          account_id: 'gmail_1', // TODO: Get from user context
          confirmed: true
        })
      });

      if (!response.ok) {
        throw new Error('Failed to execute intent');
      }

      const result = await response.json();
      setExecuteResult(result);

      // Clear input and parse result
      setInputText('');
      setParseResult(null);

      // Refresh rules list
      await fetchRules();

    } catch (error) {
      console.error('Error executing intent:', error);
      setExecuteResult({
        success: false,
        message: 'Fehler beim Ausführen der Aktion. Bitte versuche es erneut.'
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleCancel = () => {
    setParseResult(null);
    setInputText('');
  };

  const fetchRules = async () => {
    try {
      const response = await fetch('/api/preferences/rules?account_id=gmail_1');
      if (response.ok) {
        const data = await response.json();
        setRules(data.rules || []);
      }
    } catch (error) {
      console.error('Error fetching rules:', error);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Email-Präferenzen
          </h1>
          <p className="text-gray-600">
            Verwalte deine Email-Einstellungen mit natürlicher Sprache
          </p>
        </div>

        {/* Chat Interface */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">
            Präferenz-Chat
          </h2>

          <form onSubmit={handleSubmit} className="mb-4">
            <div className="flex gap-2">
              <input
                type="text"
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                placeholder="z.B. 'Alle Werbemails von Zalando muten' oder 'Amazon auf die Whitelist'"
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                disabled={isLoading}
              />
              <button
                type="submit"
                disabled={isLoading || !inputText.trim()}
                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {isLoading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Send className="w-4 h-4" />
                )}
                Senden
              </button>
            </div>
          </form>

          {/* Parsing Result */}
          {parseResult && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
              <div className="flex items-start gap-3 mb-3">
                <AlertCircle className="w-5 h-5 text-blue-600 mt-0.5" />
                <div className="flex-1">
                  <h3 className="font-semibold text-blue-900 mb-1">
                    Geparste Absicht (Confidence: {(parseResult.parsed_intent.confidence * 100).toFixed(0)}%)
                  </h3>
                  <p className="text-sm text-blue-800 mb-2">
                    {parseResult.parsed_intent.reasoning}
                  </p>

                  {/* Suggested Actions */}
                  <div className="bg-white rounded p-3 mb-3">
                    <p className="text-sm font-medium text-gray-700 mb-2">Aktion:</p>
                    <ul className="space-y-1">
                      {parseResult.suggested_actions.map((action, idx) => (
                        <li key={idx} className="text-sm text-gray-600">
                          {action}
                        </li>
                      ))}
                    </ul>
                  </div>

                  {/* Confirmation Buttons */}
                  {parseResult.requires_confirmation ? (
                    <div className="flex gap-2">
                      <button
                        onClick={handleConfirm}
                        disabled={isLoading}
                        className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:bg-gray-300 flex items-center gap-2"
                      >
                        <CheckCircle2 className="w-4 h-4" />
                        Bestätigen
                      </button>
                      <button
                        onClick={handleCancel}
                        disabled={isLoading}
                        className="px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600 disabled:bg-gray-300 flex items-center gap-2"
                      >
                        <XCircle className="w-4 h-4" />
                        Abbrechen
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={handleConfirm}
                      disabled={isLoading}
                      className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-300"
                    >
                      Ausführen
                    </button>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Execution Result */}
          {executeResult && (
            <div className={`border rounded-lg p-4 ${
              executeResult.success
                ? 'bg-green-50 border-green-200'
                : 'bg-red-50 border-red-200'
            }`}>
              <div className="flex items-center gap-2">
                {executeResult.success ? (
                  <CheckCircle2 className="w-5 h-5 text-green-600" />
                ) : (
                  <XCircle className="w-5 h-5 text-red-600" />
                )}
                <p className={`font-medium ${
                  executeResult.success ? 'text-green-900' : 'text-red-900'
                }`}>
                  {executeResult.message}
                </p>
              </div>
            </div>
          )}

          {/* Example Prompts */}
          <div className="mt-4 pt-4 border-t border-gray-200">
            <p className="text-sm font-medium text-gray-700 mb-2">Beispiele:</p>
            <div className="flex flex-wrap gap-2">
              {[
                "Amazon auf die Whitelist",
                "Werbung von Zalando muten",
                "Keine Newsletter von LinkedIn",
                "booking.com blockieren"
              ].map((example, idx) => (
                <button
                  key={idx}
                  onClick={() => setInputText(example)}
                  className="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded-full text-gray-700"
                >
                  {example}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Active Rules List */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-gray-900">
              Aktive Regeln
            </h2>
            <button
              onClick={fetchRules}
              className="text-sm text-blue-600 hover:text-blue-700"
            >
              Aktualisieren
            </button>
          </div>

          {rules.length === 0 ? (
            <p className="text-gray-500 text-center py-8">
              Keine Regeln vorhanden. Erstelle eine Regel über den Chat!
            </p>
          ) : (
            <div className="space-y-2">
              {rules.map((rule) => (
                <div
                  key={rule.id}
                  className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <p className="font-medium text-gray-900">
                        {rule.pattern}
                      </p>
                      <p className="text-sm text-gray-600 mt-1">
                        Aktion: {rule.action}
                      </p>
                      <p className="text-xs text-gray-400 mt-1">
                        Erstellt: {new Date(rule.created_at).toLocaleDateString('de-DE')} via {rule.created_via}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-1 text-xs rounded-full ${
                        rule.active
                          ? 'bg-green-100 text-green-800'
                          : 'bg-gray-100 text-gray-600'
                      }`}>
                        {rule.active ? 'Aktiv' : 'Inaktiv'}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
