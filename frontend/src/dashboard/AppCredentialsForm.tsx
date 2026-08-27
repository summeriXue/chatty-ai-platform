import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api } from '../core/api/client';
import { useCopyToClipboard } from '../agent/hooks/useCopyToClipboard';

interface AppCredentialsFormProps {
  integration: 'quickbooks' | 'google';
  currentClientId?: string;
  currentEnvironment?: string;
  redirectUri?: string;
  source?: 'stored' | 'env';
  onSaved: () => void;
  onCancel?: () => void;
}

const DOCS: Record<string, { label: string; url: string }> = {
  quickbooks: {
    label: 'Intuit Developer Portal',
    url: 'https://developer.intuit.com/app/developer/qbo/docs/get-started',
  },
  google: {
    label: 'Google Cloud Console',
    url: 'https://console.cloud.google.com/apis/credentials',
  },
};

const mono = (size: number, color = 'rgba(237,240,244,0.38)') => ({
  fontFamily: "'JetBrains Mono', ui-monospace, monospace",
  fontSize: size, letterSpacing: '0.16em',
  textTransform: 'uppercase' as const, color,
});

const inputStyle: React.CSSProperties = {
  width: '100%', boxSizing: 'border-box',
  background: 'rgba(34,40,48,0.55)', border: '1px solid rgba(230,235,242,0.14)',
  color: '#EDF0F4', borderRadius: 4, padding: '8px 12px', fontSize: 13, outline: 'none',
  fontFamily: "'Inter Tight', system-ui, sans-serif",
};

export function AppCredentialsForm({
  integration,
  currentClientId,
  currentEnvironment,
  redirectUri = 'https://auth.mechatty.com/callback',
  source,
  onSaved,
  onCancel,
}: AppCredentialsFormProps) {
  const { t } = useTranslation();
  const isEditing = !!currentClientId;
  const canOmitSecret = isEditing && source === 'stored';
  const [clientId, setClientId] = useState(currentClientId || '');
  const [clientSecret, setClientSecret] = useState('');
  const [environment, setEnvironment] = useState(currentEnvironment || (isEditing ? 'production' : 'sandbox'));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const { copied, copy } = useCopyToClipboard();

  async function handleSave() {
    if (!clientId.trim()) {
      setError(t('appCredentials.clientIdRequired'));
      return;
    }
    if (!canOmitSecret && !clientSecret.trim()) {
      setError(t('appCredentials.clientSecretRequired'));
      return;
    }
    setSaving(true); setError('');
    try {
      await api(`/api/integrations/${integration}/app-credentials`, {
        method: 'PUT',
        body: JSON.stringify({
          client_id: clientId.trim(),
          client_secret: clientSecret.trim() || null,
          environment: integration === 'quickbooks' ? environment : undefined,
        }),
      });
      onSaved();
    } catch (err: unknown) {
      setError(
        err instanceof Error
          ? err.message
          : t('appCredentials.saveFailed')
      );
    } finally {
      setSaving(false);
    }
  }

  const doc = DOCS[integration];
  const title = integration === 'quickbooks' ? 'QuickBooks' : 'Google';

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', gap: 10,
      marginTop: 12, paddingTop: 12,
      borderTop: '1px solid rgba(230,235,242,0.07)',
    }}>
      <p style={{ fontSize: 12, color: 'rgba(237,240,244,0.50)', lineHeight: 1.5 }}>
        {t('appCredentials.intro', { provider: title })}{' '}
        <a
          href={doc.url}
          target="_blank"
          rel="noopener noreferrer"
          style={{
            color: 'var(--color-ch-accent, #C8D1D9)',
            textDecoration: 'none',
          }}
        >
          {t('appCredentials.createAt', { portal: doc.label })} &rarr;
        </a>
      </p>

      {/* Redirect URI — user needs to register this in their OAuth app */}
      <div>
        <label style={{ display: 'block', ...mono(9), marginBottom: 4 }}>{t('appCredentials.redirectUri')}</label>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <input readOnly value={redirectUri} style={{ ...inputStyle, color: 'rgba(237,240,244,0.62)' }} />
          <button
            onClick={() => copy(redirectUri)}
            style={{
              padding: '8px 12px', borderRadius: 4, fontSize: 11, whiteSpace: 'nowrap',
              background: 'rgba(34,40,48,0.55)', color: copied ? '#8EA589' : 'rgba(237,240,244,0.62)',
              border: '1px solid rgba(230,235,242,0.14)', cursor: 'pointer',
            }}
          >
            {copied
              ? t('appCredentials.copied')
              : t('appCredentials.copy')}
          </button>
        </div>
        <p style={{ fontSize: 11, color: 'rgba(237,240,244,0.30)', marginTop: 3 }}>
          {t('appCredentials.redirectHint')}
        </p>
      </div>

      <div>
        <label style={{ display: 'block', ...mono(9), marginBottom: 4 }}>{t('appCredentials.clientId')}</label>
        <input
          value={clientId} onChange={e => setClientId(e.target.value)}
          placeholder={t('appCredentials.clientIdPlaceholder', {
            provider: title,
          })}
          style={inputStyle}
        />
      </div>

      <div>
        <label style={{ display: 'block', ...mono(9), marginBottom: 4 }}>{t('appCredentials.clientSecret')}</label>
        <input
          type="password"
          value={clientSecret} onChange={e => setClientSecret(e.target.value)}
          placeholder={
            canOmitSecret
              ? t('appCredentials.clientSecretUnchanged')
              : t('appCredentials.clientSecretPlaceholder', {
                  provider: title,
                })
          }
          style={inputStyle}
        />
      </div>

      {integration === 'quickbooks' && (
        <div>
          <label style={{ display: 'block', ...mono(9), marginBottom: 4 }}>{t('appCredentials.environment')}</label>
          <div style={{ display: 'flex', gap: 0, border: '1px solid rgba(230,235,242,0.07)', borderRadius: 3, overflow: 'hidden' }}>
            {([
              {
                key: 'sandbox',
                label: t('appCredentials.sandbox'),
                hint: t('appCredentials.sandboxHint'),
              },
              {
                key: 'production',
                label: t('appCredentials.production'),
                hint: t('appCredentials.productionHint'),
              },
            ] as const).map(opt => (
              <div
                key={opt.key}
                onClick={() => setEnvironment(opt.key)}
                style={{
                  flex: 1, padding: '8px 12px', cursor: 'pointer', textAlign: 'center',
                  transition: 'background 0.15s, color 0.15s',
                  background: environment === opt.key ? 'var(--color-ch-accent, #C8D1D9)' : 'transparent',
                  color: environment === opt.key ? '#0E1013' : 'rgba(237,240,244,0.62)',
                }}
              >
                <div style={{ fontSize: 12, fontWeight: environment === opt.key ? 500 : 400 }}>{opt.label}</div>
                <div style={{ fontSize: 10, marginTop: 2, opacity: 0.7 }}>{opt.hint}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {error && <p style={{ color: '#D97757', fontSize: 12 }}>{error}</p>}

      <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
        {onCancel && (
          <button onClick={onCancel} style={{
            flex: 1, padding: '8px 16px', fontSize: 13, borderRadius: 4,
            border: '1px solid rgba(230,235,242,0.14)', background: 'transparent',
            color: 'rgba(237,240,244,0.62)', cursor: 'pointer',
          }}>{t('appCredentials.cancel')}</button>
        )}
        <button onClick={handleSave} disabled={saving} style={{
          flex: 1, padding: '8px 16px', fontSize: 13, borderRadius: 4,
          background: 'var(--color-ch-accent, #C8D1D9)', color: '#0E1013',
          border: 'none', cursor: 'pointer', fontWeight: 500,
          opacity: saving ? 0.5 : 1,
        }}>
          {saving
            ? t('appCredentials.saving')
            : isEditing
              ? t('appCredentials.updateCredentials')
              : t('appCredentials.saveCredentials')}
        </button>
      </div>
    </div>
  );
}
