import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { api } from '../core/api/client';

interface Props {
  provider: string;
  onChanged?: () => void;
}

const TIERS: Array<'top' | 'mid' | 'light'> = [
  'top',
  'mid',
  'light',
];

const selectStyle: React.CSSProperties = {
  width: '100%', boxSizing: 'border-box',
  background: 'rgba(34,40,48,0.55)', border: '1px solid rgba(230,235,242,0.14)',
  color: '#EDF0F4', borderRadius: 4, padding: '6px 8px', fontSize: 12, outline: 'none',
};

const captionStyle: React.CSSProperties = {
  fontFamily: "'JetBrains Mono', ui-monospace, monospace",
  fontSize: 9, letterSpacing: '0.16em', textTransform: 'uppercase',
  color: 'rgba(237,240,244,0.38)',
};

/**
 * Lets the user override which concrete model each tier (top/mid/light) maps to.
 * Options come from the (cached) live model list; defaults are the inferred
 * values returned by /api/providers/tiers. Saving PUTs a single-tier override.
 */
export function TierPicker({ provider, onChanged }: Props) {
  const { t } = useTranslation();

  const [models, setModels] = useState<string[]>([]);
  const [tiers, setTiers] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api<{ models: string[] }>(`/api/providers/${provider}/models`)
      .then(d => setModels(d.models))
      .catch(console.error);
    api<{ tier_models: Record<string, Record<string, string>> }>('/api/providers/tiers')
      .then(d => setTiers(d.tier_models?.[provider] || {}))
      .catch(console.error);
  }, [provider]);

  async function save(tier: string, model: string) {
    const previous = tiers[tier] ?? '';
    setSaving(true);
    setTiers(prev => ({ ...prev, [tier]: model }));  // optimistic
    try {
      await api('/api/providers/tiers', {
        method: 'PUT',
        body: JSON.stringify({ provider, models: { [tier]: model } }),
      });
      onChanged?.();
    } catch (err) {
      console.error('Failed to set tier:', err);
      setTiers(prev => ({ ...prev, [tier]: previous }));  // roll back on failure
    } finally {
      setSaving(false);
    }
  }

  function getTierLabel(tier: 'top' | 'mid' | 'light'): string {
    const labels = {
      top: t('providers.tierTop'),
      mid: t('providers.tierMid'),
      light: t('providers.tierLight'),
    };

    return labels[tier];
  }

  if (!models.length) return null;

  // Keep the current resolved value selectable even if it's not in the live list.
  const optionsFor = (current: string) =>
    !current || models.includes(current) ? models : [current, ...models];

  return (
    <div>
      <label style={{ ...captionStyle, display: 'block', marginBottom: 6 }}>
        {t('providers.tiers')}
      </label>
      <div style={{ display: 'flex', gap: 8 }}>
        {TIERS.map(tier => (
          <div key={tier} style={{ flex: 1, minWidth: 0 }}>
            <span style={{ ...captionStyle, display: 'block', marginBottom: 4 }}>
              {getTierLabel(tier)}
            </span>
            <select
              value={tiers[tier] || ''}
              onChange={e => save(tier, e.target.value)}
              disabled={saving}
              style={{ ...selectStyle, opacity: saving ? 0.5 : 1 }}
            >
              <option value="">
                {t('providers.useInferredDefault')}
              </option>

              {optionsFor(tiers[tier] || '').map(m => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </div>
        ))}
      </div>
    </div>
  );
}
