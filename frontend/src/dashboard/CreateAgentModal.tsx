import { useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { api } from '../core/api/client';
import type { Agent } from '../core/types';

interface Props {
  suggestedTitle?: string;
  onClose: () => void;
  onCreated: (agent: Agent) => void;
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

export function CreateAgentModal({ suggestedTitle, onClose, onCreated }: Props) {
  const { t } = useTranslation();

  const [name, setName] = useState('');
  const [title, setTitle] = useState('');
  const [preset, setPreset] = useState<'general' | 'technical_engineer'>('general');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setLoading(true);
    setError('');
    try {
      const agent = await api<Agent>('/api/agents', {
        method: 'POST',
        body: JSON.stringify({ agent_name: name.trim(), preset}),
      });
      onCreated(agent);
      const roleParam = (title.trim() || suggestedTitle) ? `?role=${encodeURIComponent(title.trim() || suggestedTitle || '')}` : '';
      navigate(`/agent/${agent.id}${roleParam}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t('createAgent.createFailed'));
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
          marginBottom: 24, color: '#EDF0F4',
        }}>{t('createAgent.title')}</h2>

        <form onSubmit={handleSubmit}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16, marginBottom: 24 }}>

            <div>
              <label style={labelStyle}>{t('createAgent.agentType')}</label>

              <div style={{ display: 'flex', gap: 8 }}>
                <button
                  type="button"
                  onClick={() => setPreset('general')}
                  style={{
                    flex: 1,
                    padding: '10px 12px',
                    borderRadius: 4,
                    border: preset === 'general'
                      ? '1px solid #D4A85A'
                      : '1px solid rgba(230,235,242,0.14)',
                    background: preset === 'general'
                      ? 'rgba(212,168,90,0.10)'
                      : 'transparent',
                    color: preset === 'general'
                      ? '#EDF0F4'
                      : 'rgba(237,240,244,0.62)',
                    cursor: 'pointer',
                    textAlign: 'left',
                  }}
                >
                  <div style={{ fontSize: 13, fontWeight: 500 }}>
                    {t('createAgent.general')}
                  </div>

                  <div style={{
                    fontSize: 11,
                    marginTop: 3,
                    color: 'rgba(237,240,244,0.38)',
                  }}>
                    {t('createAgent.generalDesc')}
                  </div>
                </button>

                <button
                  type="button"
                  onClick={() => setPreset('technical_engineer')}
                  style={{
                    flex: 1,
                    padding: '10px 12px',
                    borderRadius: 4,
                    border: preset === 'technical_engineer'
                      ? '1px solid #D4A85A'
                      : '1px solid rgba(230,235,242,0.14)',
                    background: preset === 'technical_engineer'
                      ? 'rgba(212,168,90,0.10)'
                      : 'transparent',
                    color: preset === 'technical_engineer'
                      ? '#EDF0F4'
                      : 'rgba(237,240,244,0.62)',
                    cursor: 'pointer',
                    textAlign: 'left',
                  }}
                >
                  <div style={{ fontSize: 13, fontWeight: 500 }}>
                    {t('createAgent.technicalEngineer')}
                  </div>

                  <div style={{
                    fontSize: 11,
                    marginTop: 3,
                    color: 'rgba(237,240,244,0.38)',
                  }}>
                    {t('createAgent.technicalEngineerDesc')}
                  </div>
                </button>
              </div>
            </div>

            <div>
              <label style={labelStyle}>{t('createAgent.agentName')}</label>
              <input
                type="text"
                value={name}
                onChange={e => setName(e.target.value)}
                placeholder={t('createAgent.namePlaceholder')}
                autoFocus
                maxLength={60}
                style={inputStyle}
              />
            </div>

            <div>
              <label style={labelStyle}>{t('createAgent.titleRole')}</label>
              <input
                type="text"
                value={title}
                onChange={e => setTitle(e.target.value)}
                placeholder={suggestedTitle || t('createAgent.rolePlaceholder')}
                maxLength={80}
                style={{ ...inputStyle, color: title ? '#EDF0F4' : undefined }}
              />
              <p style={{
                fontSize: 11,
                color: 'rgba(237,240,244,0.28)',
                marginTop: 4,
              }}>
                {t('createAgent.roleHint')}
              </p>
            </div>

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
              {t('createAgent.cancel')}
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
              {loading ? t('createAgent.creating') : t('createAgent.commission')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
