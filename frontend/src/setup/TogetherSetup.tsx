import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api } from '../core/api/client';

interface Props {
  onConnected: () => void;
}

export function TogetherSetup({ onConnected }: Props) {
  const { t } = useTranslation();

  const [key, setKey] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function connect() {
    if (!key.trim()) return;
    setLoading(true);
    setError('');
    try {
      await api('/api/providers/together/connect', {
        method: 'POST',
        body: JSON.stringify({ api_key: key.trim() }),
      });
      onConnected();
    } catch (err: unknown) {
      setError(
        err instanceof Error
          ? err.message
          : t('providers.invalidApiKey')
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-3">
      <div className="bg-ch-bg-card rounded-lg px-4 py-3 space-y-2">
        <p className="text-sm text-ch-ink-mute">
          {t('providers.togetherIntro')}
        </p>
        <ol className="text-xs text-ch-ink-mute space-y-1 list-decimal list-inside">
          <li>{t('providers.togetherStepCreateAccount')}</li>
          <li>{t('providers.togetherStepCreateKey')}</li>
          <li>{t('providers.togetherStepPaste')}</li>
        </ol>
      </div>

      <input
        type="password"
        value={key}
        onChange={e => setKey(e.target.value)}
        placeholder="together_..."
        onKeyDown={e => e.key === 'Enter' && connect()}
        className="w-full bg-ch-bg-raised border border-ch-line-strong text-white rounded-lg px-4 py-3 text-sm focus:outline-none focus:border-amber-500"
      />

      {error && <p className="text-red-400 text-xs">{error}</p>}

      <a
        href="https://api.together.xyz/settings/api-keys"
        target="_blank"
        rel="noopener noreferrer"
        className="block text-xs text-ch-gold hover:text-ch-gold transition"
      >
        {t('providers.getTogetherApiKey')} &rarr;
      </a>

      <button
        onClick={connect}
        disabled={loading || !key.trim()}
        className="w-full py-2.5 bg-brand text-white text-sm font-semibold rounded-lg hover:opacity-90 transition disabled:opacity-50"
      >
        {loading
          ? t('providers.validating')
          : t('providers.connect')}
      </button>
    </div>
  );
}
