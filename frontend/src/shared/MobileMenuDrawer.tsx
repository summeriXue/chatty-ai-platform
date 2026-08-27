import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { IconBot, IconFunnel, IconChart, IconSettings } from './icons';

interface MobileMenuDrawerProps {
  onClose: () => void;
  navigate: (path: string) => void;
  children?: ReactNode;
}

export function MobileMenuDrawer({ onClose, navigate, children }: MobileMenuDrawerProps) {
  const { t } = useTranslation();

  const items = [
    {
      icon: IconBot,
      label: t('common.mobileMenu.agents'),
      action: () => {
        onClose();
        navigate('/');
      },
    },
    {
      icon: IconFunnel,
      label: 'CRM',
      action: () => {
        onClose();
        navigate('/crm');
      },
    },
    {
      icon: IconChart,
      label: t('common.mobileMenu.usage'),
      action: () => {
        onClose();
        navigate('/usage');
      },
    },
    {
      icon: IconSettings,
      label: t('common.mobileMenu.settings'),
      action: () => {
        onClose();
        document.dispatchEvent(new CustomEvent('chatty:open-settings'));
      },
    },
  ];

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 50,
        background: '#0A0C0F',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '12px 16px',
          borderBottom: '1px solid rgba(230,235,242,0.07)',
        }}
      >
        <span
          style={{
            fontFamily: "'Fraunces', Georgia, serif",
            fontSize: 20,
            color: '#EDF0F4',
          }}
        >
          {t('common.mobileMenu.menu')}
        </span>

        <div
          onClick={onClose}
          style={{
            cursor: 'pointer',
            color: 'rgba(237,240,244,0.62)',
            fontSize: 22,
            padding: '0 4px',
          }}
        >
          &times;
        </div>
      </div>

      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: 2,
          padding: '12px 16px',
        }}
      >
        {items.map(item => (
          <div
            key={item.label}
            onClick={item.action}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              padding: '12px 8px',
              borderRadius: 4,
              cursor: 'pointer',
              color: 'rgba(237,240,244,0.7)',
            }}
          >
            <item.icon size={18} strokeWidth={1.85} />
            <span style={{ fontSize: 14 }}>{item.label}</span>
          </div>
        ))}
      </div>

      {children}
    </div>
  );
}
