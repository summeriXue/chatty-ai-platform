/**
 * Chatty — AgentRemindersPanel.
 * Read-only view of all reminders for an agent, plus inferred follow-ups
 * (commitments) the agent noticed in past conversations.
 */

import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import type { TFunction } from 'i18next';
import { useNavigate } from 'react-router-dom';
import { api } from '../../core/api/client';
import { LoadError } from '../../shared/LoadError';
import { toast } from '../../shared/toast';
import type { Commitment, Reminder } from '../../core/types';

function toUTC(iso: string): Date {
  return new Date(iso.replace(' ', 'T') + 'Z');
}

function timeAgo(iso: string, t: TFunction): string {
  const d = toUTC(iso);
  const diff = Date.now() - d.getTime();
  if (diff < 0) return formatFuture(-diff, t);
  if (diff < 60000) return t('remindersPanel.time.justNow');
  if (diff < 3600000) return t('remindersPanel.time.minutesAgo', { count: Math.floor(diff / 60000) });
  if (diff < 86400000) return t('remindersPanel.time.hoursAgo', { count: Math.floor(diff / 3600000) });
  return t('remindersPanel.time.daysAgo', { count: Math.floor(diff / 86400000) });
}

function formatFuture(diff: number, t: TFunction): string {
  if (diff < 60000) return t('remindersPanel.time.inLessThanMinute');
  if (diff < 3600000) return t('remindersPanel.time.inMinutes', { count: Math.floor(diff / 60000) });
  if (diff < 86400000) return t('remindersPanel.time.inHours', { count: Math.floor(diff / 3600000) });
  return t('remindersPanel.time.inDays', { count: Math.floor(diff / 86400000) });
}

function formatDate(iso: string, locale: string): string {
  return toUTC(iso).toLocaleString(locale, {
    month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit',
  });
}

function describeRecurrence(ruleJson: string | null, t: TFunction): string | null {
  if (!ruleJson) return null;
  try {
    const rule = JSON.parse(ruleJson);
    const dayNames: Record<number, string> = {
      1: t('remindersPanel.days.mon'),
      2: t('remindersPanel.days.tue'),
      3: t('remindersPanel.days.wed'),
      4: t('remindersPanel.days.thu'),
      5: t('remindersPanel.days.fri'),
      6: t('remindersPanel.days.sat'),
      7: t('remindersPanel.days.sun'),
    };
    switch (rule.type) {
      case 'daily':
        return t('remindersPanel.recurrence.daily');
      case 'weekly': {
        const days = (rule.days || []).map((d: number) => dayNames[d] || d).join(', ');
        return t('remindersPanel.recurrence.weekly', { days });
      }
      case 'monthly':
        return t('remindersPanel.recurrence.monthly', { day: rule.day ?? '?' });
      case 'interval': {
        if (rule.hours && !rule.minutes) {
          return t('remindersPanel.recurrence.everyHours', { count: rule.hours });
        }
        if (rule.minutes && !rule.hours) {
          return t('remindersPanel.recurrence.everyMinutes', { count: rule.minutes });
        }
        return t('remindersPanel.recurrence.everyHoursMinutes', {
          hours: rule.hours || 0,
          minutes: rule.minutes || 0,
        });
      }
      case 'cron':
        return t('remindersPanel.recurrence.cron', { expression: rule.expression || '?' });
      default:
        return null;
    }
  } catch {
    return null;
  }
}

function statusLabel(status: string, t: TFunction): string {
  switch (status) {
    case 'pending': return t('remindersPanel.status.pending');
    case 'fired': return t('remindersPanel.status.fired');
    case 'cancelled': return t('remindersPanel.status.cancelled');
    default: return status;
  }
}

const statusColors: Record<string, string> = {
  pending: '#6DBF5B',
  fired: '#8B8F96',
  cancelled: '#D97757',
};

interface SeriesCache {
  [seriesId: string]: Reminder[];
}

export default function AgentRemindersPanel({ agentSlug, agentId }: { agentSlug: string; agentId: string }) {
  const { t, i18n } = useTranslation();
  const [reminders, setReminders] = useState<Reminder[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadFailed, setLoadFailed] = useState(false);
  const [retryKey, setRetryKey] = useState(0);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [seriesCache, setSeriesCache] = useState<SeriesCache>({});
  const [loadingSeries, setLoadingSeries] = useState<string | null>(null);
  const [collapsedSections, setCollapsedSections] = useState<Set<string>>(new Set());

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const result = await api<{ reminders: Reminder[] }>(`/api/reminders?agent=${agentSlug}&limit=100`);
        if (!cancelled) { setReminders(result.reminders); setLoadFailed(false); }
      } catch {
        if (!cancelled) setLoadFailed(true);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [agentSlug, retryKey]);

  const toggleSection = (section: string) => {
    setCollapsedSections(prev => {
      const next = new Set(prev);
      if (next.has(section)) next.delete(section); else next.add(section);
      return next;
    });
  };

  const loadSeries = async (seriesId: string) => {
    if (seriesCache[seriesId]) return;
    setLoadingSeries(seriesId);
    try {
      const result = await api<{ history: Reminder[] }>(`/api/reminders/series/${seriesId}?limit=20`);
      setSeriesCache(prev => ({ ...prev, [seriesId]: result.history }));
    } catch { /* ignore */ }
    setLoadingSeries(null);
  };

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-sm text-ch-ink-dim py-8 justify-center">
        <div className="animate-spin w-4 h-4 border-2 border-ch-accent border-t-transparent rounded-full" />
        {t('remindersPanel.loading')}
      </div>
    );
  }

  const pending = reminders.filter(r => r.status === 'pending')
    .sort((a, b) => a.due_at.localeCompare(b.due_at));
  const fired = reminders.filter(r => r.status === 'fired').slice(0, 20);
  const cancelled = reminders.filter(r => r.status === 'cancelled').slice(0, 10);

  const sections: { key: string; label: string; items: Reminder[]; emptyText: string }[] = [
    {
      key: 'upcoming',
      label: t('remindersPanel.sections.upcoming', { count: pending.length }),
      items: pending,
      emptyText: t('remindersPanel.sections.noPending'),
    },
    {
      key: 'completed',
      label: t('remindersPanel.sections.completed', { count: fired.length }),
      items: fired,
      emptyText: t('remindersPanel.sections.noCompleted'),
    },
    {
      key: 'cancelled',
      label: t('remindersPanel.sections.cancelled', { count: cancelled.length }),
      items: cancelled,
      emptyText: '',
    },
  ];

  const remindersContent = loadFailed && reminders.length === 0 ? (
    <LoadError
      label={t('remindersPanel.loadFailed')}
      onRetry={() => { setLoading(true); setRetryKey(k => k + 1); }}
    />
  ) : reminders.length === 0 ? (
    <div className="text-center py-12">
      <p className="text-sm text-ch-ink-dim">{t('remindersPanel.empty.title')}</p>
      <p className="text-xs text-ch-ink-dim mt-1">{t('remindersPanel.empty.description')}</p>
    </div>
  ) : (
    <>
      {sections.map(section => {
        if (section.items.length === 0 && !section.emptyText) return null;
        const isCollapsed = collapsedSections.has(section.key);
        return (
          <div key={section.key}>
            <button
              onClick={() => toggleSection(section.key)}
              className="flex items-center gap-2 mb-2 text-sm font-semibold text-ch-ink hover:text-ch-accent transition-colors w-full text-left"
            >
              <svg
                className={`w-3 h-3 text-ch-ink-dim transition-transform ${isCollapsed ? '-rotate-90' : ''}`}
                fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
              </svg>
              {section.label}
            </button>

            {!isCollapsed && (
              section.items.length === 0 ? (
                <p className="text-xs text-ch-ink-dim pl-5">{section.emptyText}</p>
              ) : (
                <div className="space-y-2">
                  {section.items.map(rem => (
                    <ReminderRow
                      key={rem.id}
                      reminder={rem}
                      isExpanded={expanded === rem.id}
                      onToggle={() => setExpanded(expanded === rem.id ? null : rem.id)}
                      seriesHistory={rem.series_id ? seriesCache[rem.series_id] : undefined}
                      loadingSeries={loadingSeries === rem.series_id}
                      onLoadSeries={() => rem.series_id && loadSeries(rem.series_id)}
                      t={t}
                      locale={i18n.language}
                    />
                  ))}
                </div>
              )
            )}
          </div>
        );
      })}
    </>
  );

  return (
    <div className="space-y-4 p-4">
      <CommitmentsSection agentId={agentId} />
      {remindersContent}
    </div>
  );
}

function formatDueDate(isoDate: string, locale: string): string {
  return new Date(isoDate + 'T00:00:00').toLocaleDateString(locale, {
    month: 'short', day: 'numeric',
  });
}

function CommitmentsSection({ agentId }: { agentId: string }) {
  const { t, i18n } = useTranslation();
  const [commitments, setCommitments] = useState<Commitment[]>([]);
  const [loadFailed, setLoadFailed] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const result = await api<{ commitments: Commitment[] }>(`/api/agents/${agentId}/commitments?status=active`);
        if (!cancelled) { setCommitments(result.commitments); setLoadFailed(false); }
      } catch {
        if (!cancelled) setLoadFailed(true);
      } finally {
        if (!cancelled) setLoaded(true);
      }
    })();
    return () => { cancelled = true; };
  }, [agentId]);

  async function act(c: Commitment, action: 'complete' | 'dismiss') {
    try {
      await api(`/api/agents/${agentId}/commitments/${c.id}/${action}`, { method: 'POST' });
      setCommitments(prev => prev.filter(x => x.id !== c.id));
      toast.success(action === 'complete' ? t('remindersPanel.followUps.toasts.completed') : t('remindersPanel.followUps.toasts.dismissed'));
    } catch {
      toast.error(action === 'complete' ? t('remindersPanel.followUps.errors.complete') : t('remindersPanel.followUps.errors.dismiss'));
    }
  }

  if (!loaded) return null;

  return (
    <div>
      <div className="flex items-center gap-2 mb-2 text-sm font-semibold text-ch-ink">
        {t('remindersPanel.followUps.title')}{commitments.length > 0 ? ` (${commitments.length})` : ''}
      </div>
      {loadFailed ? (
        <p className="text-xs text-ch-ink-dim pl-5">{t('remindersPanel.followUps.loadFailed')}</p>
      ) : commitments.length === 0 ? (
        <p className="text-xs text-ch-ink-dim pl-5">{t('remindersPanel.followUps.empty')}</p>
      ) : (
        <div className="space-y-2">
          {commitments.map(c => (
            <div key={c.id} className="border border-ch-line-strong rounded-lg bg-ch-bg-elev px-4 py-3 flex items-center gap-3">
              <div className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: '#D9A957' }} />
              <div className="flex-1 min-w-0">
                <div className="text-xs font-medium text-ch-ink">{c.text}</div>
                <div className="flex items-center gap-2 mt-0.5 text-xs text-ch-ink-dim">
                  <span>
                      {c.due_at
                        ? t('remindersPanel.followUps.due', { date: formatDueDate(c.due_at, i18n.language) })
                        : t('remindersPanel.followUps.noticed', { time: timeAgo(c.created_at, t) })}
                    </span>
                  {c.source_conversation_id && (
                    <button
                      onClick={() => navigate(`/agent/${agentId}?tab=chat&conversation=${c.source_conversation_id}`)}
                      className="text-ch-accent hover:underline"
                    >
                      {t('remindersPanel.followUps.viewConversation')}
                    </button>
                  )}
                </div>
              </div>
              <button
                onClick={() => act(c, 'complete')}
                title={t('remindersPanel.followUps.markDone')}
                className="shrink-0 w-7 h-7 flex items-center justify-center rounded text-ch-ink-dim hover:text-[#6DBF5B] hover:bg-ch-bg-raised/50 transition-colors"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
              </button>
              <button
                onClick={() => act(c, 'dismiss')}
                title={t('remindersPanel.followUps.dismiss')}
                className="shrink-0 w-7 h-7 flex items-center justify-center rounded text-ch-ink-dim hover:text-[#D97757] hover:bg-ch-bg-raised/50 transition-colors"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ReminderRow({
  reminder: rem,
  isExpanded,
  onToggle,
  seriesHistory,
  loadingSeries,
  onLoadSeries,
  t,
  locale,
}: {
  reminder: Reminder;
  isExpanded: boolean;
  onToggle: () => void;
  seriesHistory?: Reminder[];
  loadingSeries: boolean;
  onLoadSeries: () => void;
  t: TFunction;
  locale: string;
}) {
  const recurrenceDesc = describeRecurrence(rem.recurrence_rule, t);

  return (
    <div className="border border-ch-line-strong rounded-lg bg-ch-bg-elev">
      <button
        onClick={onToggle}
        className="w-full px-4 py-3 flex items-center gap-3 text-left hover:bg-ch-bg-raised/50 transition-colors rounded-lg"
      >
        <div
          className="w-2 h-2 rounded-full shrink-0"
          style={{ backgroundColor: statusColors[rem.status] || '#8B8F96' }}
        />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-medium text-ch-ink">{rem.message.length > 60 ? rem.message.slice(0, 60) + '...' : rem.message}</span>
            {recurrenceDesc && (
              <span style={{
                fontSize: 10, padding: '1px 6px', borderRadius: 4,
                backgroundColor: 'rgba(109,191,91,0.12)', color: '#6DBF5B',
                fontFamily: 'JetBrains Mono, monospace',
              }}>
                {recurrenceDesc}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2 mt-0.5">
            <span className="text-xs text-ch-ink-dim">
              {rem.status === 'pending' ? timeAgo(rem.due_at, t) : timeAgo(rem.fired_at || rem.due_at, t)}
            </span>
            {rem.status === 'pending' && (
              <span className="text-xs text-ch-ink-dim">
                ({formatDate(rem.due_at, locale)})
              </span>
            )}
          </div>
        </div>
        <svg
          className={`w-4 h-4 text-ch-ink-dim shrink-0 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
          fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {isExpanded && (
        <div className="px-4 pb-4 border-t border-ch-line-strong/50">
          <div className="mt-3 space-y-2">
            <div className="text-xs text-ch-ink">
              <span className="text-ch-ink-dim">{t('remindersPanel.details.message')}: </span>{rem.message}
            </div>
            {rem.context && (
              <div className="text-xs text-ch-ink">
                <span className="text-ch-ink-dim">{t('remindersPanel.details.context')}: </span>{rem.context}
              </div>
            )}
            <div className="flex flex-wrap gap-3 text-xs text-ch-ink-dim">
              <span>{t('remindersPanel.details.due')}: {formatDate(rem.due_at, locale)}</span>
              <span>{t('remindersPanel.details.created')}: {formatDate(rem.created_at, locale)}</span>
              {rem.fired_at && <span>{t('remindersPanel.details.fired')}: {formatDate(rem.fired_at, locale)}</span>}
              <span>{t('remindersPanel.details.status')}: {statusLabel(rem.status, t)}</span>
            </div>

            {rem.result && (
              <div className="mt-2">
                <div className="text-xs text-ch-ink-dim mb-1">{t('remindersPanel.details.result')}:</div>
                <div className="text-xs text-ch-ink-mute bg-ch-bg-raised/50 px-3 py-2 rounded max-h-32 overflow-auto whitespace-pre-wrap">
                  {rem.result}
                </div>
              </div>
            )}

            {rem.is_recurring && rem.series_id && (
              <div className="mt-2">
                {seriesHistory ? (
                  <div>
                    <div className="text-xs text-ch-ink-dim mb-1">{t('remindersPanel.details.seriesHistory', { count: seriesHistory.length })}</div>
                    <div className="space-y-1 max-h-32 overflow-auto">
                      {seriesHistory.map(h => (
                        <div key={h.id} className="flex items-center gap-2 text-xs">
                          <div
                            className="w-1.5 h-1.5 rounded-full shrink-0"
                            style={{ backgroundColor: statusColors[h.status] || '#8B8F96' }}
                          />
                          <span className="text-ch-ink-dim">{formatDate(h.due_at, locale)}</span>
                          <span className="text-ch-ink-dim">{statusLabel(h.status, t)}</span>
                          {h.result && (
                            <span className="text-ch-ink-mute truncate">{h.result.slice(0, 60)}</span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <button
                    onClick={onLoadSeries}
                    disabled={loadingSeries}
                    className="text-xs text-ch-accent hover:underline"
                  >
                    {loadingSeries ? t('remindersPanel.details.loading') : t('remindersPanel.details.viewSeriesHistory')}
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
