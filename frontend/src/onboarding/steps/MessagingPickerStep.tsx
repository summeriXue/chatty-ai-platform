import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { api } from '../../core/api/client';
import type { Integration } from '../../core/types';

const MESSAGING_IDS = ['telegram', 'whatsapp'];

interface Props {
  onComplete: (selectedIds: string[]) => void;
  onSkip: () => void;
}

export function MessagingPickerStep({ onComplete, onSkip }: Props) {
  const { t } = useTranslation();
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api<{ integrations: Integration[] }>('/api/integrations')
      .then(data => {
        const messaging = data.integrations.filter(
          i => MESSAGING_IDS.includes(i.id) && !i.configured
        );
        setIntegrations(messaging);
      })
      // best-effort: an empty list still lets the user skip this step
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  function toggle(id: string) {
    setSelected(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <div className="w-6 h-6 border-2 border-ch-gold border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div>
      <h2 className="text-xl font-bold text-white mb-2">{t('onboarding.messaging.title')}</h2>
      <p className="text-gray-400 text-sm mb-6">
        {t('onboarding.messaging.intro')}
      </p>

      {integrations.length === 0 ? (
        <div className="text-center py-8">
          <p className="text-gray-400">{t('onboarding.messaging.alreadyConfigured')}</p>
          <button
            onClick={onSkip}
            className="mt-4 w-full py-3 bg-brand text-white font-semibold rounded-xl hover:opacity-90 transition"
          >
            {t('onboarding.messaging.continue')}
          </button>
        </div>
      ) : (
        <>
          <div className="space-y-2 mb-8">
            {integrations.map(integration => {
              const isSelected = selected.has(integration.id);
              const isRecommended = integration.id === 'telegram';
              return (
                <button
                  key={integration.id}
                  onClick={() => toggle(integration.id)}
                  className={`w-full flex items-center gap-4 p-4 rounded-xl border transition text-left ${
                    isSelected
                      ? 'bg-ch-gold/10 border-ch-gold/50'
                      : 'bg-gray-800 border-gray-700 hover:border-gray-600'
                  }`}
                >
                  <div className={`w-5 h-5 rounded border-2 flex items-center justify-center flex-shrink-0 transition ${
                    isSelected ? 'bg-ch-gold border-ch-gold' : 'border-gray-600'
                  }`}>
                    {isSelected && (
                      <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                      </svg>
                    )}
                  </div>
                  <span className="text-2xl">{integration.icon}</span>
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <p className="text-white font-medium">{integration.name}</p>
                      {isRecommended && (
                        <span className="text-xs bg-green-900/40 text-green-400 border border-green-700/40 rounded-full px-2 py-0.5">
                          {t('onboarding.messaging.recommended')}
                        </span>
                      )}
                    </div>
                    <p className="text-gray-400 text-xs mt-0.5">
                      {t(`integrations.descriptions.${integration.id}`, { defaultValue: integration.description })}
                    </p>
                  </div>
                </button>
              );
            })}
          </div>

          <p className="text-gray-500 text-xs text-center mb-4">
            {t('onboarding.messaging.footnote')}
          </p>

          <div className="flex gap-3">
            <button
              onClick={onSkip}
              className="flex-1 py-3 rounded-xl border border-gray-700 text-gray-400 hover:bg-gray-800 transition font-medium"
            >
              {t('onboarding.messaging.skipForNow')}
            </button>
            <button
              onClick={() => onComplete(Array.from(selected))}
              disabled={selected.size === 0}
              className="flex-1 py-3 bg-brand text-white font-semibold rounded-xl hover:opacity-90 transition disabled:opacity-30 disabled:cursor-not-allowed"
            >
              {t('onboarding.messaging.continue')}
            </button>
          </div>
        </>
      )}
    </div>
  );
}
