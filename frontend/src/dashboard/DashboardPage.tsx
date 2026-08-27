import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useOutletContext } from 'react-router-dom';
import { api } from '../core/api/client';
import { AgentCard } from './AgentCard';
import { CreateAgentModal } from './CreateAgentModal';
import { ImportAgentModal } from './ImportAgentModal';
import { WarmHalo } from '../shared/WarmHalo';
import { LoadError } from '../shared/LoadError';
import { IconSearch, IconPlus, IconDownload } from '../shared/icons';
import { MobileMenuDrawer } from '../shared/MobileMenuDrawer';
import { useIsMobile } from '../shared/useIsMobile';
import type { Agent, BrandingConfig, ProviderStatus } from '../core/types';

const SUGGESTED_ROLES = [
  'personalAssistant',
  'apClerk',
  'arClerk',
  'customerService',
  'purchasing',
  'salesRep',
  'salesSupport',
  'researchAnalyst',
  'bookkeeper',
  'hrCoordinator',
  'marketingAssistant',
  'operationsManager',
] as const;

const mono = (size: number, color = 'rgba(237,240,244,0.38)') => ({
  fontFamily: "'JetBrains Mono', ui-monospace, monospace",
  fontSize: size, letterSpacing: '0.16em',
  textTransform: 'uppercase' as const, color,
});

export function DashboardPage() {
  const { t, i18n } = useTranslation();
  const [agents, setAgents] = useState<Agent[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [showImport, setShowImport] = useState(false);
  const [suggestedTitle, setSuggestedTitle] = useState('');
  const [loading, setLoading] = useState(true);
  const [loadFailed, setLoadFailed] = useState(false);
  const navigate = useNavigate();
  const context = useOutletContext<{ branding: BrandingConfig | null; setBranding: (b: BrandingConfig) => void }>();
  const branding = context?.branding;

  // No synchronous setState here — the initial state is already
  // loading=true/loadFailed=false, and the retry handler resets both before
  // calling. Keeping it out lets the effect call this without tripping the
  // react-hooks/set-state-in-effect rule.
  const loadDashboard = useCallback(() => {
    Promise.all([
      api<{ agents: Agent[] }>('/api/agents'),
      api<ProviderStatus>('/api/providers'),
    ]).then(([agentsData, providerData]) => {
      const anyProviderConfigured = Object.values(providerData.profiles).some(p => p.configured);
      if (!anyProviderConfigured) {
        navigate('/setup', { replace: true });
        return;
      }
      setAgents(agentsData.agents);
    }).catch(err => {
      console.error('Dashboard load error:', err);
      setLoadFailed(true);
    }).finally(() => setLoading(false));
  }, [navigate]);

  useEffect(() => { loadDashboard(); }, [loadDashboard]);

  const isMobile = useIsMobile();
  const [showMenu, setShowMenu] = useState(false);
  const companyName = branding?.company_name || 'Chatty';
  const hour = new Date().getHours();
  const greeting = hour < 12
    ? t('dashboard.goodMorning')
    : hour < 17
      ? t('dashboard.goodAfternoon')
      : t('dashboard.goodEvening');

  const dateLocale = i18n.language === 'zh-CN' ? 'zh-CN' : 'en-US';
  const formattedDate = new Date().toLocaleDateString(dateLocale, {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
  });

  return (
    <div style={{ height: '100%', overflow: 'auto', position: 'relative' }}>
      <WarmHalo />

      {/* Top bar */}
      <div style={{
        height: 48, display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: isMobile ? '0 16px' : '0 24px', borderBottom: '1px solid rgba(230,235,242,0.07)',
        position: 'relative', zIndex: 2,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          {isMobile && (
            <div
              onClick={() => setShowMenu(true)}
              style={{ cursor: 'pointer', color: 'rgba(237,240,244,0.62)', fontSize: 18 }}
            >&#9776;</div>
          )}
          <div style={mono(10, 'rgba(237,240,244,0.62)')}>
            {companyName} · {formattedDate}
          </div>
        </div>
        {!isMobile && (
          <div style={{
            padding: '5px 12px', borderRadius: 4,
            background: 'rgba(245,239,227,0.04)', border: '1px solid rgba(230,235,242,0.07)',
            fontFamily: "'JetBrains Mono', ui-monospace, monospace",
            fontSize: 11, color: 'rgba(237,240,244,0.62)',
            display: 'flex', gap: 8, alignItems: 'center', cursor: 'pointer',
          }}>
            <IconSearch size={13} strokeWidth={1.85} /> {t('dashboard.searchPlaceholder')}
            <span style={{ color: 'rgba(237,240,244,0.38)', marginLeft: 20, letterSpacing: '0.1em' }}>⌘K</span>
          </div>
        )}
      </div>

      {isMobile && showMenu && (
        <MobileMenuDrawer onClose={() => setShowMenu(false)} navigate={navigate} />
      )}

      {/* Hero */}
      <div style={{
        padding: isMobile ? '28px 20px 20px' : '44px 44px 28px', borderBottom: '1px solid rgba(230,235,242,0.07)',
        position: 'relative', zIndex: 2,
      }}>
        <h1 style={{
          fontFamily: "'Fraunces', Georgia, serif",
          fontSize: isMobile ? 36 : 54, fontWeight: 400, letterSpacing: '-0.028em',
          lineHeight: 1.02, margin: 0, color: '#EDF0F4',
        }}>
          {greeting}.
        </h1>
        <div style={{
          fontFamily: "'Fraunces', Georgia, serif",
          fontSize: 22, fontStyle: 'italic',
          color: 'rgba(237,240,244,0.62)', marginTop: 10,
          letterSpacing: '-0.01em', lineHeight: 1.35,
        }}>
          {loading ? t('dashboard.loadingAgents') : agents.length === 0 ? (
            t('dashboard.noAgentsHero')
          ) : (
            <>
              {t('dashboard.youHave')}{' '}
              <span style={{ color: '#D4A85A', fontStyle: 'normal' }}>
                {t('dashboard.agentCount', { count: agents.length })}
              </span>{' '}
              {t('dashboard.readyToWork')}
            </>
          )}
        </div>

        {/* Stats strip */}
        {!loading && agents.length > 0 && (
          <div style={{
            display: 'flex', gap: 48, marginTop: 28, paddingTop: 22,
            borderTop: '1px dashed rgba(230,235,242,0.07)',
          }}>
            {[
              [t('dashboard.agents'), String(agents.length), null],
            ].map(([label, value, sub]) => (
              <div key={label as string}>
                <div style={mono(9, 'rgba(237,240,244,0.38)')}>{label}</div>
                <div style={{
                  fontFamily: "'Fraunces', Georgia, serif",
                  fontSize: 26, lineHeight: 1, fontWeight: 400,
                  letterSpacing: '-0.02em', marginTop: 6, color: '#EDF0F4',
                }}>{value}</div>
                {sub && <div style={{ fontSize: 10, color: 'rgba(237,240,244,0.38)', marginTop: 4 }}>{sub}</div>}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Agents */}
      <div style={{ padding: isMobile ? '16px 20px 32px' : '22px 44px 40px', position: 'relative', zIndex: 2 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
          <div style={mono(10, 'rgba(237,240,244,0.38)')}>
            {t('dashboard.yourAgents')} · {agents.length}
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              onClick={() => setShowImport(true)}
              style={{
                background: 'transparent', color: 'rgba(237,240,244,0.62)',
                border: '1px solid rgba(230,235,242,0.14)',
                fontSize: 12, padding: '6px 12px', borderRadius: 4,
                display: 'flex', alignItems: 'center', gap: 6,
                cursor: 'pointer', fontFamily: "'Inter Tight', system-ui, sans-serif",
              }}
            >
              <IconDownload size={13} strokeWidth={2.25} /> {t('dashboard.importAgent')}
            </button>
            <button
              onClick={() => setShowCreate(true)}
              style={{
                background: 'transparent', color: '#EDF0F4',
                border: '1px solid rgba(230,235,242,0.14)',
                fontSize: 12, padding: '6px 12px', borderRadius: 4,
                display: 'flex', alignItems: 'center', gap: 6,
                cursor: 'pointer', fontFamily: "'Inter Tight', system-ui, sans-serif",
              }}
            >
              <IconPlus size={13} strokeWidth={2.25} /> {t('dashboard.commissionAgent')}
            </button>
          </div>
        </div>

        {loading ? (
          <div style={{ display: 'flex', justifyContent: 'center', padding: '80px 0' }}>
            <div className="w-8 h-8 border-2 border-ch-accent border-t-transparent rounded-full animate-spin" />
          </div>
        ) : loadFailed ? (
          <LoadError label={t('dashboard.loadAgentsFailed')} onRetry={() => { setLoading(true); setLoadFailed(false); loadDashboard(); }} />
        ) : agents.length === 0 ? (
          <div>
            <div style={{
              fontFamily: "'Fraunces', Georgia, serif",
              fontSize: 22, fontWeight: 400, letterSpacing: '-0.01em',
              color: 'rgba(237,240,244,0.62)', marginBottom: 16,
            }}>
              {t('dashboard.buildTeam')}
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : 'repeat(3, 1fr)', gap: 8 }}>
              {SUGGESTED_ROLES.map(key => (
                <div
                  key={key}
                  onClick={() => {
                    setSuggestedTitle(t(`dashboard.roles.${key}.role`));
                    setShowCreate(true);
                  }}
                  style={{
                    background: 'rgba(20,24,30,0.78)',
                    border: '1px dashed rgba(230,235,242,0.14)',
                    borderRadius: 6, padding: isMobile ? '12px 16px' : '14px 16px',
                    cursor: 'pointer',
                    display: isMobile ? 'flex' : 'block',
                    alignItems: 'baseline',
                    gap: isMobile ? 10 : undefined,
                  }}
                  onMouseEnter={e => { (e.currentTarget as HTMLElement).style.borderColor = 'rgba(212,168,90,0.4)'; (e.currentTarget as HTMLElement).style.borderStyle = 'solid'; }}
                  onMouseLeave={e => { (e.currentTarget as HTMLElement).style.borderColor = 'rgba(230,235,242,0.14)'; (e.currentTarget as HTMLElement).style.borderStyle = 'dashed'; }}
                >
                  <div style={{
                    fontFamily: "'Fraunces', Georgia, serif",
                    fontSize: isMobile ? 15 : 17, letterSpacing: '-0.01em', color: '#EDF0F4',
                    marginBottom: isMobile ? 0 : 4,
                    flexShrink: 0,
                  }}>
                    {t(`dashboard.roles.${key}.role`)}
                  </div>
                  <div style={{
                    fontSize: 12, color: 'rgba(237,240,244,0.38)', lineHeight: 1.4,
                  }}>
                    {t(`dashboard.roles.${key}.desc`)}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : 'repeat(3, 1fr)', gap: 8 }}>
            {agents.map(agent => (
              <AgentCard key={agent.id} agent={agent} />
            ))}
          </div>
        )}

        {/* Suggested roles — show when fewer than 8 agents */}
        {!loading && agents.length > 0 && agents.length < 8 && (
          <div style={{ marginTop: 32 }}>
            <div style={{
              fontFamily: "'Fraunces', Georgia, serif",
              fontSize: 18, fontWeight: 400, letterSpacing: '-0.01em',
              color: 'rgba(237,240,244,0.5)', marginBottom: 14,
            }}>
              {t('dashboard.teamIdeas')}
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : 'repeat(4, 1fr)', gap: 8 }}>
              {SUGGESTED_ROLES.map(key => (
                <div
                  key={key}
                  onClick={() => {
                    setSuggestedTitle(t(`dashboard.roles.${key}.role`));
                    setShowCreate(true);
                  }}
                  style={{
                    background: 'transparent',
                    border: '1px dashed rgba(230,235,242,0.08)',
                    borderRadius: 6, padding: '10px 14px',
                    cursor: 'pointer',
                  }}
                  onMouseEnter={e => { (e.currentTarget as HTMLElement).style.borderColor = 'rgba(212,168,90,0.3)'; (e.currentTarget as HTMLElement).style.borderStyle = 'solid'; (e.currentTarget as HTMLElement).style.background = 'rgba(20,24,30,0.4)'; }}
                  onMouseLeave={e => { (e.currentTarget as HTMLElement).style.borderColor = 'rgba(230,235,242,0.08)'; (e.currentTarget as HTMLElement).style.borderStyle = 'dashed'; (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
                >
                  <div style={{
                    fontSize: 14, color: 'rgba(237,240,244,0.5)', letterSpacing: '-0.01em',
                  }}>
                    {t(`dashboard.roles.${key}.role`)}
                  </div>
                  <div style={{
                    fontSize: 11, color: 'rgba(237,240,244,0.25)', marginTop: 3, lineHeight: 1.3,
                  }}>
                    {t(`dashboard.roles.${key}.desc`)}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {showCreate && (
        <CreateAgentModal
          suggestedTitle={suggestedTitle}
          onClose={() => { setShowCreate(false); setSuggestedTitle(''); }}
          onCreated={agent => {
            setAgents(prev => [...prev, agent]);
            setShowCreate(false);
            setSuggestedTitle('');
          }}
        />
      )}

      {showImport && (
        <ImportAgentModal onClose={() => setShowImport(false)} />
      )}
    </div>
  );
}
