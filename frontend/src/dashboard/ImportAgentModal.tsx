import { useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { api } from '../core/api/client';

interface Props {
  onClose: () => void;
}

const labelStyle: React.CSSProperties = {
  display: 'block',
  fontFamily: "'JetBrains Mono', ui-monospace, monospace",
  fontSize: 9, letterSpacing: '0.16em', textTransform: 'uppercase',
  color: 'rgba(237,240,244,0.38)', marginBottom: 6,
};

const inputStyle: React.CSSProperties = {
  width: '100%', boxSizing: 'border-box',
  background: 'rgba(20,24,30,0.78)',
  border: '1px solid rgba(230,235,242,0.14)',
  color: '#EDF0F4', borderRadius: 4,
  padding: '10px 14px', fontSize: 14,
  outline: 'none',
  fontFamily: "'Inter Tight', system-ui, sans-serif",
};

export function ImportAgentModal({ onClose }: Props) {
  const { t } = useTranslation();

  const [name, setName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setLoading(true);
    setError('');
    try {
      const result = await api<{
        agent_id: string;
        agent_slug: string;
        conversation_id: string;
        session_token: string;
      }>('/api/agents/import/start', {
        method: 'POST',
        body: JSON.stringify({ agent_name: name.trim() }),
      });
      navigate(`/agent/${result.agent_id}?conversation=${result.conversation_id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t('importAgent.startFailed'));
      setLoading(false);
    }
  }

  return (
    <div
      style={{
        position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)',
        display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50,
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: '#11141A', borderRadius: 6,
          border: '1px solid rgba(230,235,242,0.14)',
          padding: 32, width: '100%', maxWidth: 420,
          boxShadow: '0 8px 40px rgba(0,0,0,0.5)',
        }}
        onClick={e => e.stopPropagation()}
      >
        <h2 style={{
          fontFamily: "'Fraunces', Georgia, serif",
          fontSize: 24, fontWeight: 400, letterSpacing: '-0.02em',
          marginBottom: 8, color: '#EDF0F4',
        }}>{t('importAgent.title')}</h2>

        <p style={{
          fontSize: 13, color: 'rgba(237,240,244,0.5)',
          marginBottom: 24, lineHeight: 1.5,
        }}>
          {t('importAgent.description')}
        </p>

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: 24 }}>
            <label style={labelStyle}>{t('importAgent.agentName')}</label>
            <input
              type="text"
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder={t('importAgent.namePlaceholder')}
              autoFocus
              maxLength={60}
              style={inputStyle}
            />
            <p style={{
              fontSize: 11, color: 'rgba(237,240,244,0.28)', marginTop: 4,
            }}>{t('importAgent.nameHint')}</p>
          </div>

          {error && <p style={{ color: '#D97757', fontSize: 13, marginBottom: 16 }}>{error}</p>}

          <div style={{ display: 'flex', gap: 8 }}>
            <button
              type="button"
              onClick={onClose}
              style={{
                flex: 1, padding: '9px 16px', borderRadius: 4,
                border: '1px solid rgba(230,235,242,0.14)',
                background: 'transparent', color: 'rgba(237,240,244,0.62)',
                cursor: 'pointer', fontSize: 13,
              }}
            >
              {t('importAgent.cancel')}
            </button>
            <button
              type="submit"
              disabled={loading || !name.trim()}
              style={{
                flex: 1, padding: '9px 16px', borderRadius: 4,
                background: '#D4A85A', color: '#0E1013',
                border: 'none', fontWeight: 500, cursor: 'pointer', fontSize: 13,
                opacity: (loading || !name.trim()) ? 0.5 : 1,
              }}
            >
              {loading
                ? t('importAgent.starting')
                : t('importAgent.startImport')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
