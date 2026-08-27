/**
 * Chatty — error boundary for render/lifecycle crashes (async/event errors
 * are the toast layer's job). Two mounts:
 *  - main.tsx: wraps <App/> with RootErrorFallback (full-screen, reload)
 *  - AppShell.tsx: wraps the route <Outlet/> with RouteErrorFallback, keyed
 *    by pathname — a crashed page dies alone while the nav rail survives
 */

import { Component } from 'react';
import type { ErrorInfo, ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  INK, INK_DIM, INK_MUTE, INK_SOFT, LINE_STRONG, ACCENT, ACCENT_INK,
  FONT_DISPLAY, FONT_SANS, FONT_MONO, mono,
} from './styles';

interface Props {
  fallback: (error: Error, reset: () => void) => ReactNode;
  children: ReactNode;
}

interface State {
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('ErrorBoundary caught:', error, info.componentStack);
  }

  reset = () => {
    this.setState({ error: null });
  };

  render() {
    if (this.state.error) return this.props.fallback(this.state.error, this.reset);
    return this.props.children;
  }
}

interface ErrorDetailProps {
  error: Error;
  /** Redact error.message in prod builds (set on the unauthenticated root fallback). */
  redactMessage?: boolean;
}

/** Stack traces — and, for the root fallback, error messages — are an
 *  info-disclosure risk on the unauthenticated login page (the root boundary
 *  wraps it). Dev builds show message + stack; prod shows error.message for
 *  the authenticated route fallback only, and a generic pointer to the
 *  console for the root fallback. */
function ErrorDetail({ error, redactMessage }: ErrorDetailProps) {
  const { t } = useTranslation();

  const detail = import.meta.env.DEV
    ? `${error.message}\n${error.stack ?? ''}`
    : redactMessage
      ? t('common.errorBoundary.detailsLogged')
      : error.message;

  return (
    <details style={{ marginTop: 24, maxWidth: 560, width: '100%' }}>
      <summary style={{ ...mono(10, INK_DIM), cursor: 'pointer' }}>
        {t('common.errorBoundary.errorDetail')}
      </summary>

      <pre
        style={{
          fontFamily: FONT_MONO,
          fontSize: 11,
          color: INK_DIM,
          whiteSpace: 'pre-wrap',
          overflowWrap: 'break-word',
          maxHeight: 240,
          overflowY: 'auto',
          margin: '8px 0 0',
          padding: 12,
          border: `1px solid ${LINE_STRONG}`,
          borderRadius: 6,
          textAlign: 'left',
        }}
      >
        {detail}
      </pre>
    </details>
  );
}

const buttonStyle = {
  padding: '9px 20px',
  borderRadius: 4,
  background: ACCENT,
  color: ACCENT_INK,
  border: 'none',
  fontWeight: 500,
  cursor: 'pointer',
  fontSize: 13,
  fontFamily: FONT_SANS,
} as const;

const secondaryButtonStyle = {
  ...buttonStyle,
  background: 'transparent',
  color: INK_MUTE,
  border: `1px solid ${LINE_STRONG}`,
} as const;

interface RootErrorFallbackProps {
  error: Error;
}

export function RootErrorFallback({ error }: RootErrorFallbackProps) {
  const { t } = useTranslation();

  // No router hooks here — this mounts outside BrowserRouter.
  return (
    <div
      style={{
        minHeight: '100svh',
        background: '#0A0C0F',
        color: INK,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 24,
        textAlign: 'center',
        fontFamily: FONT_SANS,
      }}
    >
      <h1
        style={{
          fontFamily: FONT_DISPLAY,
          fontSize: 28,
          fontWeight: 400,
          letterSpacing: '-0.02em',
          margin: '0 0 8px',
        }}
      >
        {t('common.errorBoundary.rootTitle')}
      </h1>

      <p
        style={{
          fontSize: 13,
          color: INK_SOFT,
          lineHeight: 1.5,
          margin: '0 0 24px',
        }}
      >
        {t('common.errorBoundary.rootDescription')}
      </p>

      <button onClick={() => window.location.reload()} style={buttonStyle}>
        {t('common.errorBoundary.reload')}
      </button>

      <ErrorDetail error={error} redactMessage />
    </div>
  );
}

interface RouteErrorFallbackProps {
  error: Error;
  reset: () => void;
}

export function RouteErrorFallback({ error, reset }: RouteErrorFallbackProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();

  // The explicit reset() matters when the crashed route IS '/': the
  // boundary's pathname key doesn't change, so navigation alone would
  // leave it stuck in its error state.
  function handleBackToDashboard() {
    navigate('/');
    reset();
  }

  return (
    <div
      style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 24,
        textAlign: 'center',
        color: INK,
        fontFamily: FONT_SANS,
      }}
    >
      <h2
        style={{
          fontFamily: FONT_DISPLAY,
          fontSize: 24,
          fontWeight: 400,
          letterSpacing: '-0.02em',
          margin: '0 0 8px',
        }}
      >
        {t('common.errorBoundary.routeTitle')}
      </h2>

      <p
        style={{
          fontSize: 13,
          color: INK_SOFT,
          lineHeight: 1.5,
          margin: '0 0 24px',
        }}
      >
        {t('common.errorBoundary.routeDescription')}
      </p>

      <div style={{ display: 'flex', gap: 8 }}>
        <button onClick={handleBackToDashboard} style={buttonStyle}>
          {t('common.errorBoundary.backToDashboard')}
        </button>

        <button
          onClick={() => window.location.reload()}
          style={secondaryButtonStyle}
        >
          {t('common.errorBoundary.reload')}
        </button>
      </div>

      <ErrorDetail error={error} />
    </div>
  );
}
