import { useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { api } from '../core/api/client';
import type { Agent } from '../core/types';

interface Props {
  agent: Agent;
  onClose: () => void;
  onDeleted: (id: string) => void;
}

export function DeleteAgentModal({ agent, onClose, onDeleted }: Props) {
  const { t } = useTranslation();

  const [confirmation, setConfirmation] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const confirmPhrase = t('deleteAgent.confirmPhrase', {
    name: agent.agent_name.toLowerCase(),
  });

  const canDelete = confirmation.toLowerCase() === confirmPhrase.toLowerCase();

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!canDelete) return;

    setLoading(true);
    setError('');

    try {
      await api(`/api/agents/${agent.id}`, { method: 'DELETE' });
      onDeleted(agent.id);
    } catch (err: unknown) {
      setError(
        err instanceof Error
          ? err.message
          : t('deleteAgent.errors.deleteFailed')
      );
      setLoading(false);
    }
  }

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.6)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 50,
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: '#11141A',
          borderRadius: 6,
          border: '1px solid rgba(230,235,242,0.14)',
          padding: 32,
          width: '100%',
          maxWidth: 420,
          boxShadow: '0 8px 40px rgba(0,0,0,0.5)',
        }}
        onClick={e => e.stopPropagation()}
      >
        <h2
          style={{
            fontFamily: "'Fraunces', Georgia, serif",
            fontSize: 24,
            fontWeight: 400,
            letterSpacing: '-0.02em',
            marginBottom: 8,
            color: '#EDF0F4',
          }}
        >
          {t('deleteAgent.title')}
        </h2>

        <p
          style={{
            fontSize: 13,
            color: 'rgba(237,240,244,0.5)',
            marginBottom: 8,
            lineHeight: 1.5,
          }}
        >
          {t('deleteAgent.descriptionBefore')}{' '}
          <strong style={{ color: '#EDF0F4' }}>
            {agent.agent_name}
          </strong>{' '}
          {t('deleteAgent.descriptionAfter')}
        </p>

        <div
          style={{
            background: 'rgba(217,119,87,0.08)',
            border: '1px solid rgba(217,119,87,0.2)',
            borderRadius: 6,
            padding: '12px 14px',
            marginBottom: 20,
          }}
        >
          <p
            style={{
              fontSize: 12,
              color: '#D97757',
              margin: 0,
              lineHeight: 1.5,
            }}
          >
            {t('deleteAgent.confirmInstructionBefore')}{' '}
            <strong
              style={{
                fontFamily: "'JetBrains Mono', ui-monospace, monospace",
                background: 'rgba(217,119,87,0.12)',
                padding: '1px 6px',
                borderRadius: 3,
              }}
            >
              {confirmPhrase}
            </strong>{' '}
            {t('deleteAgent.confirmInstructionAfter')}
          </p>
        </div>

        <form onSubmit={handleSubmit}>
          <input
            type="text"
            value={confirmation}
            onChange={e => setConfirmation(e.target.value)}
            placeholder={confirmPhrase}
            autoFocus
            autoComplete="off"
            style={{
              width: '100%',
              boxSizing: 'border-box',
              background: 'rgba(20,24,30,0.78)',
              border: '1px solid rgba(230,235,242,0.14)',
              color: '#EDF0F4',
              borderRadius: 4,
              padding: '10px 14px',
              fontSize: 14,
              outline: 'none',
              marginBottom: 20,
              fontFamily: "'Inter Tight', system-ui, sans-serif",
            }}
          />

          {error && (
            <p
              style={{
                color: '#D97757',
                fontSize: 13,
                marginBottom: 16,
              }}
            >
              {error}
            </p>
          )}

          <div style={{ display: 'flex', gap: 8 }}>
            <button
              type="button"
              onClick={onClose}
              style={{
                flex: 1,
                padding: '9px 16px',
                borderRadius: 4,
                border: '1px solid rgba(230,235,242,0.14)',
                background: 'transparent',
                color: 'rgba(237,240,244,0.62)',
                cursor: 'pointer',
                fontSize: 13,
              }}
            >
              {t('deleteAgent.cancel')}
            </button>

            <button
              type="submit"
              disabled={loading || !canDelete}
              style={{
                flex: 1,
                padding: '9px 16px',
                borderRadius: 4,
                background: canDelete ? '#D97757' : 'rgba(217,119,87,0.3)',
                color: canDelete ? '#0E1013' : 'rgba(14,16,19,0.5)',
                border: 'none',
                fontWeight: 500,
                cursor: canDelete ? 'pointer' : 'default',
                fontSize: 13,
                transition: 'background 0.15s, color 0.15s',
              }}
            >
              {loading
                ? t('deleteAgent.deleting')
                : t('deleteAgent.deletePermanently')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
