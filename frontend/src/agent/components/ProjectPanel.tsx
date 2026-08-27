import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { api } from '../../core/api/client';

type Props = {
  agentId: string;
  projectRoot?: string;
  onSaved?: (projectRoot: string) => void;
};

export function ProjectPanel({
  agentId,
  projectRoot = '',
  onSaved,
}: Props) {
  const { t } = useTranslation();

  const [value, setValue] = useState(projectRoot);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    setValue(projectRoot);
  }, [projectRoot]);

  async function handleSave() {
    setSaving(true);
    setSaved(false);
    setError('');

    try {
      const updated = await api<{ project_root: string }>(
        `/api/agents/${agentId}`,
        {
          method: 'PUT',
          body: JSON.stringify({
            project_root: value.trim(),
          }),
        },
      );

      const nextRoot = updated.project_root || '';
      setValue(nextRoot);
      setSaved(true);
      onSaved?.(nextRoot);
    } catch (err: unknown) {
      setError(
        err instanceof Error
          ? err.message
          : t('projectPanel.saveFailed'),
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <div
      style={{
        flex: 1,
        overflow: 'auto',
        padding: 32,
      }}
    >
      <div style={{ maxWidth: 720 }}>
        <h2
          style={{
            fontFamily: "'Fraunces', Georgia, serif",
            fontSize: 24,
            fontWeight: 400,
            color: '#EDF0F4',
            marginBottom: 8,
          }}
        >
          {t('projectPanel.title')}
        </h2>

        <p
          style={{
            fontSize: 13,
            lineHeight: 1.6,
            color: 'rgba(237,240,244,0.5)',
            marginBottom: 28,
          }}
        >
          {t('projectPanel.description')}
        </p>

        <label
          style={{
            display: 'block',
            fontSize: 11,
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
            color: 'rgba(237,240,244,0.5)',
            marginBottom: 8,
          }}
        >
          {t('projectPanel.projectRoot')}
        </label>

        <input
          type="text"
          value={value}
          onChange={e => {
            setValue(e.target.value);
            setSaved(false);
          }}
          placeholder="E:\Dev\Projects\my-project"
          style={{
            width: '100%',
            boxSizing: 'border-box',
            padding: '10px 12px',
            borderRadius: 4,
            border: '1px solid rgba(230,235,242,0.14)',
            background: '#11141A',
            color: '#EDF0F4',
            fontSize: 13,
            fontFamily: "'JetBrains Mono', ui-monospace, monospace",
            outline: 'none',
          }}
        />

        <p
          style={{
            marginTop: 8,
            fontSize: 11,
            color: 'rgba(237,240,244,0.32)',
          }}
        >
          {t('projectPanel.backendAccess')}
        </p>

        {error && (
          <p
            style={{
              color: '#D97757',
              fontSize: 12,
              marginTop: 12,
            }}
          >
            {error}
          </p>
        )}

        {saved && (
          <p
            style={{
              color: 'rgba(237,240,244,0.6)',
              fontSize: 12,
              marginTop: 12,
            }}
          >
            {t('projectPanel.saved')}
          </p>
        )}

        <button
          type="button"
          onClick={handleSave}
          disabled={saving}
          style={{
            marginTop: 20,
            padding: '9px 18px',
            borderRadius: 4,
            border: 'none',
            background: '#D4A85A',
            color: '#0E1013',
            fontSize: 13,
            fontWeight: 500,
            cursor: saving ? 'default' : 'pointer',
            opacity: saving ? 0.5 : 1,
          }}
        >
          {saving
            ? t('projectPanel.saving')
            : t('projectPanel.saveProject')}
        </button>
      </div>
    </div>
  );
}
