import { useTranslation } from 'react-i18next';
import type { CrmDeal } from '../../core/types';
import { STAGE_COLORS } from '../constants';
import { mono, INK, INK_MUTE, INK_DIM, LINE_STRONG, ACCENT_INK, GOLD, SAGE, FONT_DISPLAY } from '../../shared/styles';
import { modalOverlay, modalContent, mobileDragHandle, btnDanger } from '../styles';

interface DealDetailSheetProps {
  deal: CrmDeal;
  isMobile: boolean;
  onClose: () => void;
  onEdit: (deal: CrmDeal) => void;
  onStageChange: (deal: CrmDeal, stage: string) => void;
}

export function DealDetailSheet({ deal, isMobile, onClose, onEdit, onStageChange }: DealDetailSheetProps) {
  const { t } = useTranslation();

  return (
    <div
      onClick={onClose}
      style={modalOverlay(isMobile)}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={modalContent(isMobile)}
      >
        {isMobile && (
          <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 16 }}>
            <div style={mobileDragHandle} />
          </div>
        )}

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
          <h3 style={{
            fontFamily: FONT_DISPLAY,
            fontSize: 20, fontWeight: 400, letterSpacing: '-0.01em',
            color: INK, margin: 0, flex: 1,
          }}>{deal.title}</h3>
          <span style={{
            fontFamily: FONT_DISPLAY,
            fontSize: 20, color: GOLD, flexShrink: 0, marginLeft: 12,
          }}>${deal.value.toLocaleString()}</span>
        </div>

        <div style={{
          fontSize: 12, color: INK_MUTE, marginBottom: 16,
        }}>
          {t('crmDealDetail.stage')}: {' '}
          <span style={{ color: STAGE_COLORS[deal.stage]?.color || INK }}>
            {t(`crmDealDetail.stages.${deal.stage}`, { defaultValue: deal.stage })}
          </span>
        </div>

        {deal.notes && (
          <p style={{ fontSize: 14, color: INK_MUTE, marginBottom: 16, lineHeight: 1.5 }}>
            {deal.notes}
          </p>
        )}

        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 20 }}>
          {deal.contact_name && (
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ ...mono(10), color: INK_DIM }}>{t('crmDealDetail.contact')}</span>
              <span style={{ fontSize: 13, color: INK }}>{deal.contact_name}</span>
            </div>
          )}
          {deal.probability > 0 && (
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ ...mono(10), color: INK_DIM }}>{t('crmDealDetail.probability')}</span>
              <span style={{ fontSize: 13, color: INK }}>{deal.probability}%</span>
            </div>
          )}
          {deal.expected_close_date && (
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ ...mono(10), color: INK_DIM }}>{t('crmDealDetail.expectedClose')}</span>
              <span style={{ fontSize: 13, color: INK }}>{deal.expected_close_date}</span>
            </div>
          )}
        </div>

        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <button onClick={onClose} style={{
            padding: '10px 16px', borderRadius: 6,
            border: `1px solid ${LINE_STRONG}`, background: 'transparent',
            color: INK_MUTE, fontSize: 13, cursor: 'pointer',
          }}>{t('crmDealDetail.close')}</button>
          <button onClick={() => onEdit(deal)} style={{
            padding: '10px 16px', borderRadius: 6,
            border: `1px solid ${LINE_STRONG}`, background: 'transparent',
            color: INK, fontSize: 13, cursor: 'pointer',
          }}>{t('crmDealDetail.edit')}</button>
          {deal.stage !== 'won' && deal.stage !== 'lost' && (
            <>
              <button onClick={() => onStageChange(deal, 'won')} style={{
                padding: '10px 16px', borderRadius: 6,
                background: SAGE, color: ACCENT_INK,
                border: 'none', fontWeight: 500, fontSize: 13, cursor: 'pointer',
                flex: 1,
              }}>{t('crmDealDetail.markWon')}</button>
              <button onClick={() => onStageChange(deal, 'lost')} style={{
                ...btnDanger,
                padding: '10px 16px', borderRadius: 6, fontSize: 13,
              }}>{t('crmDealDetail.markLost')}</button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
