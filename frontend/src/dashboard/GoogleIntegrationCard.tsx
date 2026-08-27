import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { api } from '../core/api/client';
import { useOAuthFlow } from '../core/hooks/useOAuthFlow';
import { AppCredentialsForm } from './AppCredentialsForm';
import type {
  Integration,
  Agent,
  GoogleAccount,
  GmailScopeLevel,
  CalendarScopeLevel,
  DriveScopeLevel,
} from '../core/types';

interface Props {
  integration: Integration;
  onChanged: () => void;
}

const GMAIL_SCOPE_VALUES: GmailScopeLevel[] = ['none', 'read', 'send'];
const CALENDAR_SCOPE_VALUES: CalendarScopeLevel[] = ['none', 'read', 'full'];
const DRIVE_SCOPE_VALUES: DriveScopeLevel[] = ['none', 'file', 'readonly', 'full'];

export function GoogleIntegrationCard({ integration, onChanged }: Props) {
  const { t } = useTranslation();
  const [pickerOpen, setPickerOpen] = useState(false);
  const [editingAccountId, setEditingAccountId] = useState('');
  const [gmail, setGmail]       = useState<GmailScopeLevel>('none');
  const [calendar, setCalendar] = useState<CalendarScopeLevel>('none');
  const [drive, setDrive]       = useState<DriveScopeLevel>('none');
  const [disconnecting, setDisconnecting] = useState('');
  const [localError, setLocalError] = useState('');
  const [showCredForm, setShowCredForm] = useState(false);
  const [existingCreds, setExistingCreds] = useState<{ client_id?: string; redirect_uri?: string; source?: 'stored' | 'env' }>({});
  const [assignmentsOpen, setAssignmentsOpen] = useState(false);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [savingAgent, setSavingAgent] = useState('');
  const hasAppCreds = integration.has_app_credentials !== false;
  const accounts = integration.google_accounts || [];

  const gmailOptions = GMAIL_SCOPE_VALUES.map(value => ({
    value,
    label: t(`googleIntegration.gmail.${value}.label`),
    hint: t(`googleIntegration.gmail.${value}.hint`),
  }));

  const calendarOptions = CALENDAR_SCOPE_VALUES.map(value => ({
    value,
    label: t(`googleIntegration.calendar.${value}.label`),
    hint: t(`googleIntegration.calendar.${value}.hint`),
  }));

  const driveOptions = DRIVE_SCOPE_VALUES.map(value => ({
    value,
    label: t(`googleIntegration.drive.${value}.label`),
    hint: t(`googleIntegration.drive.${value}.hint`),
  }));

  function scopeValueLabel(service: 'gmail' | 'calendar' | 'drive', value: string): string {
    return t(`googleIntegration.scopeValues.${service}.${value}`, { defaultValue: value });
  }

  function scopeSummary(grants: GoogleAccount['scope_grants']): string {
    return [
      grants.gmail !== 'none' &&
        `${t('googleIntegration.services.gmail')}: ${scopeValueLabel('gmail', grants.gmail)}`,
      grants.calendar !== 'none' &&
        `${t('googleIntegration.services.calendar')}: ${scopeValueLabel('calendar', grants.calendar)}`,
      grants.drive !== 'none' &&
        `${t('googleIntegration.services.drive')}: ${scopeValueLabel('drive', grants.drive)}`,
    ].filter(Boolean).join(' · ');
  }

  const oauth = useOAuthFlow();

  useEffect(() => {
    if (oauth.state.status === 'success') {
      setPickerOpen(false);
      setEditingAccountId('');
      onChanged();
      oauth.reset();
    }
  }, [oauth.state.status]);  // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (assignmentsOpen && agents.length === 0) {
      // best-effort: assignment list stays empty on failure
      api<{ agents: Agent[] }>('/api/agents').then(data => setAgents(data.agents)).catch(() => {});
    }
  }, [assignmentsOpen]); // eslint-disable-line react-hooks/exhaustive-deps

  async function openCredForm() {
    setLocalError('');
    try {
      const existing = await api<{ configured: boolean; client_id?: string; redirect_uri?: string; source?: 'stored' | 'env' }>('/api/integrations/google/app-credentials');
      setExistingCreds(existing.configured
        ? { client_id: existing.client_id, redirect_uri: existing.redirect_uri, source: existing.source }
        : { redirect_uri: existing.redirect_uri });
    } catch { setExistingCreds({}); }
    setShowCredForm(true);
  }

  function openScopePicker(accountId: string = '', acct?: GoogleAccount) {
    setEditingAccountId(accountId);
    setGmail(acct?.scope_grants?.gmail ?? 'none');
    setCalendar(acct?.scope_grants?.calendar ?? 'none');
    setDrive(acct?.scope_grants?.drive ?? 'none');
    setPickerOpen(true);
    setLocalError('');
  }

  const anyGranted = gmail !== 'none' || calendar !== 'none' || drive !== 'none';

  async function connect() {
    setLocalError('');
    if (!anyGranted) {
      setLocalError(t('googleIntegration.enableOneService'));
      return;
    }
    const base = editingAccountId
      ? `/api/integrations/google/${editingAccountId}/setup`
      : '/api/integrations/google/setup';
    const complete = editingAccountId
      ? `/api/integrations/google/${editingAccountId}/setup/complete`
      : '/api/integrations/google/setup/complete';
    await oauth.start({
      setupUrl: base,
      setupBody: { gmail_level: gmail, calendar_level: calendar, drive_level: drive },
      completeUrl: complete,
    });
  }

  async function disconnectAccount(accountId: string) {
    setDisconnecting(accountId); setLocalError('');
    try {
      await api(`/api/integrations/google/${accountId}/disconnect`, { method: 'POST' });
      onChanged();
      if (assignmentsOpen) {
        api<{ agents: Agent[] }>('/api/agents').then(data => setAgents(data.agents)).catch(() => {});
      }
    } catch (err: unknown) {
      setLocalError(err instanceof Error ? err.message : t('googleIntegration.disconnectFailed'));
    } finally {
      setDisconnecting('');
    }
  }

  async function toggleAgentAccount(agentId: string, service: 'gmail' | 'calendar' | 'drive', accountId: string) {
    setSavingAgent(agentId);
    const agent = agents.find(a => a.id === agentId);
    const current = agent?.google_accounts || {};
    const currentList = current[service] || [];
    const newList = currentList.includes(accountId)
      ? currentList.filter(id => id !== accountId)
      : [...currentList, accountId];
    const updated = { ...current, [service]: newList };
    try {
      await api(`/api/agents/${agentId}`, {
        method: 'PUT',
        body: JSON.stringify({ google_accounts: updated }),
      });
      const data = await api<{ agents: Agent[] }>('/api/agents');
      setAgents(data.agents);
    } catch (err: unknown) {
      setLocalError(err instanceof Error ? err.message : t('googleIntegration.updateAgentFailed'));
    } finally {
      setSavingAgent('');
    }
  }

  function accountsForService(service: 'gmail' | 'calendar' | 'drive') {
    return accounts.filter(a => {
      const g = a.scope_grants;
      if (service === 'gmail') return g.gmail !== 'none';
      if (service === 'calendar') return g.calendar !== 'none';
      return g.drive !== 'none';
    });
  }

  const isRunning = oauth.state.status === 'starting' ||
                    oauth.state.status === 'awaiting_user' ||
                    oauth.state.status === 'completing';

  return (
    <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-2xl">{integration.icon}</span>
          <div>
            <p className="text-white font-medium">{integration.name}</p>
            <p className="text-gray-400 text-xs mt-0.5">
              {accounts.length === 0
                ? t('googleIntegration.description')
                : t('googleIntegration.accountsConnected', { count: accounts.length })}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {accounts.length === 0 && !hasAppCreds && (
            <button onClick={openCredForm} disabled={isRunning}
              className="text-xs px-3 py-1.5 rounded-lg bg-gray-700 text-gray-300 hover:bg-gray-600 transition disabled:opacity-50">
              {t('googleIntegration.setup')}
            </button>
          )}
          {accounts.length === 0 && hasAppCreds && (
            <button onClick={() => openScopePicker()} disabled={isRunning}
              className="text-xs px-3 py-1.5 rounded-lg bg-gray-700 text-gray-300 hover:bg-gray-600 transition disabled:opacity-50">
              {isRunning ? t('googleIntegration.connecting') : t('googleIntegration.connect')}
            </button>
          )}
          {accounts.length > 0 && (
            <>
              <button onClick={() => openScopePicker()} disabled={isRunning}
                className="text-xs px-3 py-1.5 rounded-lg bg-brand text-white hover:opacity-90 transition disabled:opacity-50">
                {t('googleIntegration.addAccount')}
              </button>
              <button onClick={openCredForm}
                className="text-xs px-2 py-1.5 rounded-lg text-gray-500 hover:text-gray-300 hover:bg-gray-700 transition">
                {t('googleIntegration.editCredentials')}
              </button>
            </>
          )}
        </div>
      </div>

      {/* Error / OAuth status */}
      {localError && <p className="mt-2 text-red-400 text-xs">{localError}</p>}
      {oauth.state.status === 'error' && oauth.state.error && (
        <p className="mt-2 text-red-400 text-xs">{oauth.state.error}</p>
      )}
      {isRunning && (
        <p className="mt-2 text-indigo-300 text-xs flex items-center gap-2">
          <span className="w-3 h-3 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin inline-block" />
          {oauth.state.status === 'starting' && t('googleIntegration.preparingAuthorization')}
          {oauth.state.status === 'awaiting_user' && t('googleIntegration.completeAuthorization')}
          {oauth.state.status === 'completing' && t('googleIntegration.finalizingConnection')}
        </p>
      )}

      {/* App credentials form */}
      {showCredForm && (
        <AppCredentialsForm
          integration="google"
          currentClientId={existingCreds.client_id}
          redirectUri={existingCreds.redirect_uri}
          source={existingCreds.source}
          onSaved={() => { setShowCredForm(false); onChanged(); }}
          onCancel={() => setShowCredForm(false)}
        />
      )}

      {/* Connected accounts list */}
      {accounts.length > 0 && (
        <div className="mt-3 space-y-2">
          {accounts.map(acct => (
            <div key={acct.id} className="flex items-center justify-between bg-gray-900/50 rounded-lg px-3 py-2">
              <div>
                <p className="text-white text-xs font-medium">
                  {acct.email}
                  {acct.connection_status === 'broken' && (
                    <span className="ml-2 text-red-400 text-[10px] bg-red-900/20 px-1.5 py-0.5 rounded">{t('googleIntegration.connectionLost')}</span>
                  )}
                </p>
                <p className="text-gray-500 text-[11px] mt-0.5">{scopeSummary(acct.scope_grants)}</p>
              </div>
              <div className="flex items-center gap-1.5">
                <button onClick={() => openScopePicker(acct.id, acct)} disabled={isRunning}
                  className="text-[11px] px-2 py-1 rounded text-gray-400 hover:text-gray-200 hover:bg-gray-700 transition disabled:opacity-50">
                  {acct.connection_status === 'broken' ? t('googleIntegration.reconnect') : t('googleIntegration.changeScopes')}
                </button>
                <button onClick={() => disconnectAccount(acct.id)} disabled={disconnecting === acct.id || isRunning}
                  className="text-[11px] px-2 py-1 rounded text-gray-500 hover:text-red-400 hover:bg-gray-700 transition disabled:opacity-50">
                  {disconnecting === acct.id ? '...' : t('googleIntegration.disconnect')}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Agent Assignments */}
      {accounts.length > 0 && (
        <div className="mt-3">
          <button onClick={() => setAssignmentsOpen(!assignmentsOpen)}
            className="text-xs text-gray-400 hover:text-gray-200 transition flex items-center gap-1">
            <span className={`transition-transform ${assignmentsOpen ? 'rotate-90' : ''}`}>&#9654;</span>
            {t('googleIntegration.agentAssignments')}
          </button>
          {assignmentsOpen && (
            <div className="mt-2 space-y-2">
              {agents.length === 0 && <p className="text-gray-500 text-xs">{t('googleIntegration.noAgents')}</p>}
              {agents.map(agent => {
                const ga = agent.google_accounts || {};
                return (
                  <div key={agent.id} className="bg-gray-900/30 rounded-lg px-3 py-2">
                    <p className="text-white text-xs font-medium mb-1.5">{agent.agent_name}</p>
                    <div className="grid grid-cols-3 gap-2">
                      {(['gmail', 'calendar', 'drive'] as const).map(svc => {
                        const available = accountsForService(svc);
                        const selected = ga[svc] || [];
                        return (
                          <div key={svc}>
                            <label className="text-gray-500 text-[10px] uppercase tracking-wide block mb-0.5">
                              {svc === 'gmail'
                                ? t('googleIntegration.services.gmail')
                                : svc === 'calendar'
                                  ? t('googleIntegration.services.calendarFull')
                                  : t('googleIntegration.services.driveFull')}
                            </label>
                            {available.length === 0 && (
                              <span className="text-gray-600 text-[10px]">{t('googleIntegration.noAccounts')}</span>
                            )}
                            <div className="space-y-0.5">
                              {available.map((a, i) => (
                                <label key={a.id} className="flex items-center gap-1.5 text-[11px] text-gray-300 cursor-pointer">
                                  <input
                                    type="checkbox"
                                    checked={selected.includes(a.id)}
                                    onChange={() => toggleAgentAccount(agent.id, svc, a.id)}
                                    disabled={savingAgent === agent.id}
                                    className="rounded border-gray-600 bg-gray-800 text-indigo-500 w-3 h-3 accent-indigo-500"
                                  />
                                  <span>{a.email}{selected.includes(a.id) && i === 0 && selected[0] === a.id && selected.length > 1 ? ` (${t('googleIntegration.default')})` : ''}</span>
                                </label>
                              ))}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Scope picker panel */}
      {pickerOpen && (
        <div className="mt-4 pt-4 border-t border-gray-700 space-y-4">
          <p className="text-gray-400 text-xs">
            {editingAccountId
              ? t('googleIntegration.updateScopesDescription')
              : t('googleIntegration.newAccountScopesDescription')}
          </p>
          <ScopeGroup
            title={t('googleIntegration.services.gmail')}
            options={gmailOptions}
            value={gmail}
            onChange={(v) => setGmail(v as GmailScopeLevel)}
          />

          <ScopeGroup
            title={t('googleIntegration.services.calendarFull')}
            options={calendarOptions}
            value={calendar}
            onChange={(v) => setCalendar(v as CalendarScopeLevel)}
          />

          <ScopeGroup
            title={t('googleIntegration.services.driveFull')}
            options={driveOptions}
            value={drive}
            onChange={(v) => setDrive(v as DriveScopeLevel)}
          />

          <div className="flex gap-2 pt-2">
            <button onClick={() => { setPickerOpen(false); setEditingAccountId(''); }} disabled={isRunning}
              className="flex-1 py-2 text-sm rounded-lg border border-gray-600 text-gray-400 hover:bg-gray-700 transition disabled:opacity-50">
              {t('googleIntegration.cancel')}
            </button>
            <button onClick={connect} disabled={isRunning || !anyGranted}
              className="flex-1 py-2 text-sm rounded-lg bg-brand text-white font-medium disabled:opacity-50">
              {isRunning ? t('googleIntegration.connecting') : editingAccountId ? t('googleIntegration.reconnect') : t('googleIntegration.connectGoogleAccount')}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}


interface ScopeGroupProps {
  title: string;
  options: { value: string; label: string; hint: string }[];
  value: string;
  onChange: (v: string) => void;
}

function ScopeGroup({ title, options, value, onChange }: ScopeGroupProps) {
  return (
    <div>
      <p className="text-white text-sm font-medium mb-2">{title}</p>
      <div className="space-y-1.5">
        {options.map(opt => (
          <label
            key={opt.value}
            className={`flex items-start gap-2 p-2 rounded-lg cursor-pointer transition ${
              value === opt.value ? 'bg-indigo-900/30 border border-indigo-700' : 'bg-gray-900/50 border border-transparent hover:bg-gray-900'
            }`}
          >
            <input
              type="radio"
              checked={value === opt.value}
              onChange={() => onChange(opt.value)}
              className="mt-0.5 accent-indigo-500"
            />
            <div>
              <p className="text-white text-xs font-medium">{opt.label}</p>
              <p className="text-gray-400 text-[11px] leading-snug">{opt.hint}</p>
            </div>
          </label>
        ))}
      </div>
    </div>
  );
}
