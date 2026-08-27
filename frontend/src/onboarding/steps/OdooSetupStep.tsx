import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api } from '../../core/api/client';

interface Props {
  onComplete: () => void;
  onSkip: () => void;
}

export function OdooSetupStep({ onComplete, onSkip }: Props) {
  const { t } = useTranslation();

  const [url, setUrl] = useState('');
  const [database, setDatabase] = useState('');
  const [username, setUsername] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const [discoveredDbs, setDiscoveredDbs] = useState<string[]>([]);
  const [discovering, setDiscovering] = useState(false);
  const [discoveryMethod, setDiscoveryMethod] = useState('');
  const [manualMode, setManualMode] = useState(false);

  async function discoverDatabases() {
    if (!url.trim()) return;
    setDiscovering(true);
    setError('');
    setDiscoveredDbs([]);
    setDiscoveryMethod('');

    try {
      const result = await api<{
        databases: string[];
        method: string | null;
        error: string | null;
      }>('/api/integrations/odoo/discover-databases', {
        method: 'POST',
        body: JSON.stringify({ url }),
      });

      if (result.databases.length > 0) {
        setDiscoveredDbs(result.databases);
        setDiscoveryMethod(result.method || '');
        setManualMode(false);

        if (result.databases.length === 1) {
          setDatabase(result.databases[0]);
        }
      } else {
        setError(
          result.error || t('onboarding.odoo.noDatabasesFound')
        );
      }
    } catch {
      setError(t('onboarding.odoo.couldNotReach'));
    } finally {
      setDiscovering(false);
    }
  }

  async function connect() {
    setSaving(true);
    setError('');

    try {
      await api('/api/integrations/odoo/setup', {
        method: 'POST',
        body: JSON.stringify({
          url,
          database,
          username,
          api_key: apiKey,
        }),
      });

      onComplete();
    } catch (err: unknown) {
      setError(
        err instanceof Error
          ? err.message
          : t('onboarding.odoo.connectionFailed')
      );
    } finally {
      setSaving(false);
    }
  }

  const isValid =
    url.trim() &&
    database.trim() &&
    username.trim() &&
    apiKey.trim();

  const showDropdown = discoveredDbs.length > 0 && !manualMode;

  return (
    <div>
      <h2 className="text-xl font-bold text-white mb-2">
        {t('onboarding.odoo.title')}
      </h2>

      <p className="text-gray-400 text-sm mb-6">
        {t('onboarding.odoo.description')}
      </p>

      <div className="space-y-4 mb-6">
        {/* URL */}
        <div>
          <label className="block text-sm text-gray-300 mb-1.5">
            {t('onboarding.odoo.url')}
          </label>

          <input
            value={url}
            onChange={e => {
              setUrl(e.target.value);

              if (discoveredDbs.length > 0) {
                setDiscoveredDbs([]);
                setDiscoveryMethod('');
                setDatabase('');
                setManualMode(false);
              }
            }}
            placeholder="https://mycompany.odoo.com"
            className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-4 py-3 text-sm focus:outline-none focus:border-amber-500"
          />

          <div className="flex items-center justify-between mt-1.5">
            <p className="text-gray-500 text-xs">
              {t('onboarding.odoo.urlHelp')}
            </p>

            <button
              onClick={discoverDatabases}
              disabled={discovering || !url.trim()}
              className="text-amber-400 text-xs hover:text-amber-300 transition disabled:opacity-30 disabled:cursor-not-allowed"
            >
              {discovering
                ? t('onboarding.odoo.searching')
                : t('onboarding.odoo.findDatabase')}
            </button>
          </div>
        </div>

        {/* Database */}
        <div>
          <label className="block text-sm text-gray-300 mb-1.5">
            {t('onboarding.odoo.databaseName')}
          </label>

          {showDropdown ? (
            <>
              <select
                value={database}
                onChange={e => setDatabase(e.target.value)}
                className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-4 py-3 text-sm focus:outline-none focus:border-amber-500 appearance-none"
              >
                <option value="">
                  {t('onboarding.odoo.selectDatabase')}
                </option>

                {discoveredDbs.map(db => (
                  <option key={db} value={db}>
                    {db}
                  </option>
                ))}
              </select>

              <div className="flex items-center justify-between mt-1.5">
                <p className="text-gray-500 text-xs">
                  {discoveredDbs.length === 1
                    ? t('onboarding.odoo.databaseFound')
                    : t('onboarding.odoo.databasesFound', {
                        count: discoveredDbs.length,
                      })}

                  {discoveryMethod === 'url_inference' &&
                    ` ${t('onboarding.odoo.inferredFromUrl')}`}
                </p>

                <button
                  onClick={() => setManualMode(true)}
                  className="text-gray-500 text-xs hover:text-gray-400 transition"
                >
                  {t('onboarding.odoo.typeManually')}
                </button>
              </div>
            </>
          ) : (
            <>
              <input
                value={database}
                onChange={e => setDatabase(e.target.value)}
                placeholder="mycompany-main"
                className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-4 py-3 text-sm focus:outline-none focus:border-amber-500"
              />

              {discoveredDbs.length > 0 && manualMode && (
                <div className="flex items-center justify-between mt-1.5">
                  <p className="text-gray-500 text-xs">
                    {t('onboarding.odoo.enterDatabaseName')}
                  </p>

                  <button
                    onClick={() => setManualMode(false)}
                    className="text-gray-500 text-xs hover:text-gray-400 transition"
                  >
                    {t('onboarding.odoo.useDiscoveredDatabases')}
                  </button>
                </div>
              )}

              {discoveredDbs.length === 0 && !manualMode && (
                <p className="text-gray-500 text-xs mt-1.5">
                  {t('onboarding.odoo.databaseHelp')}
                </p>
              )}
            </>
          )}
        </div>

        {/* Username */}
        <div>
          <label className="block text-sm text-gray-300 mb-1.5">
            {t('onboarding.odoo.username')}
          </label>

          <input
            value={username}
            onChange={e => setUsername(e.target.value)}
            placeholder="admin@mycompany.com"
            className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-4 py-3 text-sm focus:outline-none focus:border-amber-500"
          />

          <p className="text-gray-500 text-xs mt-1">
            {t('onboarding.odoo.usernameHelp')}
          </p>
        </div>

        {/* API Key */}
        <div>
          <label className="block text-sm text-gray-300 mb-1.5">
            {t('onboarding.odoo.apiKey')}
          </label>

          <input
            type="password"
            value={apiKey}
            onChange={e => setApiKey(e.target.value)}
            placeholder={t('onboarding.odoo.apiKeyPlaceholder')}
            className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-4 py-3 text-sm focus:outline-none focus:border-amber-500"
          />

          <p className="text-gray-500 text-xs mt-1">
            {t('onboarding.odoo.apiKeyHelp')}
          </p>
        </div>
      </div>

      {error && (
        <div className="text-red-400 text-sm bg-red-900/20 rounded-lg px-4 py-3 mb-4">
          {error}
        </div>
      )}

      <div className="flex gap-3">
        <button
          onClick={onSkip}
          className="flex-1 py-3 rounded-xl border border-gray-700 text-gray-400 hover:bg-gray-800 transition font-medium"
        >
          {t('onboarding.odoo.skip')}
        </button>

        <button
          onClick={connect}
          disabled={saving || !isValid}
          className="flex-1 py-3 bg-brand text-white font-semibold rounded-xl hover:opacity-90 transition disabled:opacity-30 disabled:cursor-not-allowed"
        >
          {saving
            ? t('onboarding.odoo.connecting')
            : t('onboarding.odoo.connect')}
        </button>
      </div>
    </div>
  );
}
