import { useTranslation } from 'react-i18next';

const statusMap = {
  live: {
    color: 'var(--color-ch-accent, #C8D1D9)',
    labelKey: 'common.status.live',
    glow: true,
  },
  idle: {
    color: '#8EA589',
    labelKey: 'common.status.ready',
    glow: false,
  },
  off: {
    color: 'rgba(237,240,244,0.38)',
    labelKey: 'common.status.asleep',
    glow: false,
  },
} as const;

interface StatusDotProps {
  status: 'live' | 'idle' | 'off';
  showLabel?: boolean;
}

export function StatusDot({ status, showLabel = true }: StatusDotProps) {
  const { t } = useTranslation();
  const s = statusMap[status] ?? statusMap.idle;
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      <div style={{
        width: 6, height: 6, borderRadius: '50%',
        background: s.color,
        boxShadow: s.glow ? `0 0 10px ${s.color}` : 'none',
      }} />
      {showLabel && (
        <span style={{
          fontFamily: "'JetBrains Mono', ui-monospace, monospace",
          fontSize: 10, letterSpacing: '0.16em',
          textTransform: 'uppercase',
          color: 'rgba(237,240,244,0.62)',
        }}>{t(s.labelKey)}</span>
      )}
    </div>
  );
}
