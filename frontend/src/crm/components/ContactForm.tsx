import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api } from '../../core/api/client';
import { labelStyle, inputStyle, CORAL } from '../../shared/styles';
import { formModalOverlay, formModalContent, formTitle, btnPrimary, btnSecondary } from '../styles';
import type { CrmContact } from '../../core/types';

interface Props {
  contact?: CrmContact;
  onClose: () => void;
  onSaved: () => void;
}

export function ContactForm({ contact, onClose, onSaved }: Props) {
  const { t } = useTranslation();
  const isEdit = !!contact;
  const [name, setName] = useState(contact?.name || '');
  const [email, setEmail] = useState(contact?.email || '');
  const [phone, setPhone] = useState(contact?.phone || '');
  const [company, setCompany] = useState(contact?.company || '');
  const [title, setTitle] = useState(contact?.title || '');
  const [source, setSource] = useState(contact?.source || '');
  const [status, setStatus] = useState(contact?.status || 'active');
  const [tags, setTags] = useState(contact?.tags || '');
  const [notes, setNotes] = useState(contact?.notes || '');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) {
      setError(t('crmContactForm.errors.nameRequired'));
      return;
    }

    setSaving(true);
    setError('');

    try {
      if (isEdit) {
        await api(`/api/crm/contacts/${contact.id}`, {
          method: 'PUT',
          body: JSON.stringify({
            name,
            email,
            phone,
            company,
            title,
            source,
            status,
            tags,
            notes,
          }),
        });
      } else {
        await api('/api/crm/contacts', {
          method: 'POST',
          body: JSON.stringify({
            name,
            email,
            phone,
            company,
            title,
            source,
            status,
            tags,
            notes,
          }),
        });
      }

      onSaved();
    } catch (err: unknown) {
      setError(
        err instanceof Error
          ? err.message
          : t('crmContactForm.errors.saveFailed'),
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <div style={formModalOverlay} onClick={onClose}>
      <form
        onClick={e => e.stopPropagation()}
        onSubmit={handleSubmit}
        style={formModalContent()}
      >
        <h2 style={formTitle}>
          {isEdit
            ? t('crmContactForm.editTitle')
            : t('crmContactForm.newTitle')}
        </h2>

        {error && (
          <p style={{ color: CORAL, fontSize: 12, marginBottom: 12 }}>
            {error}
          </p>
        )}

        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div>
            <label style={labelStyle}>
              {t('crmContactForm.fields.name')} *
            </label>
            <input
              value={name}
              onChange={e => setName(e.target.value)}
              style={inputStyle}
            />
          </div>

          <div>
            <label style={labelStyle}>
              {t('crmContactForm.fields.email')}
            </label>
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              style={inputStyle}
            />
          </div>

          <div>
            <label style={labelStyle}>
              {t('crmContactForm.fields.phone')}
            </label>
            <input
              type="tel"
              value={phone}
              onChange={e => setPhone(e.target.value)}
              style={inputStyle}
            />
          </div>

          <div>
            <label style={labelStyle}>
              {t('crmContactForm.fields.company')}
            </label>
            <input
              value={company}
              onChange={e => setCompany(e.target.value)}
              style={inputStyle}
            />
          </div>

          <div>
            <label style={labelStyle}>
              {t('crmContactForm.fields.jobTitle')}
            </label>
            <input
              value={title}
              onChange={e => setTitle(e.target.value)}
              style={inputStyle}
            />
          </div>

          <div>
            <label style={labelStyle}>
              {t('crmContactForm.fields.source')}
            </label>
            <select
              value={source}
              onChange={e => setSource(e.target.value)}
              style={inputStyle}
            >
              <option value="">
                {t('crmContactForm.source.select')}
              </option>
              <option value="referral">
                {t('crmContactForm.source.referral')}
              </option>
              <option value="website">
                {t('crmContactForm.source.website')}
              </option>
              <option value="cold_call">
                {t('crmContactForm.source.coldCall')}
              </option>
              <option value="social">
                {t('crmContactForm.source.socialMedia')}
              </option>
              <option value="event">
                {t('crmContactForm.source.event')}
              </option>
              <option value="other">
                {t('crmContactForm.source.other')}
              </option>
            </select>
          </div>

          <div>
            <label style={labelStyle}>
              {t('crmContactForm.fields.status')}
            </label>
            <select
              value={status}
              onChange={e => setStatus(e.target.value)}
              style={inputStyle}
            >
              <option value="active">
                {t('crmContactForm.status.active')}
              </option>
              <option value="inactive">
                {t('crmContactForm.status.inactive')}
              </option>
              <option value="archived">
                {t('crmContactForm.status.archived')}
              </option>
            </select>
          </div>

          <div>
            <label style={labelStyle}>
              {t('crmContactForm.fields.tags')}
            </label>
            <input
              value={tags}
              onChange={e => setTags(e.target.value)}
              style={inputStyle}
            />
          </div>

          <div>
            <label style={labelStyle}>
              {t('crmContactForm.fields.notes')}
            </label>
            <textarea
              value={notes}
              onChange={e => setNotes(e.target.value)}
              rows={3}
              style={{ ...inputStyle, resize: 'none' }}
            />
          </div>
        </div>

        <div style={{ display: 'flex', gap: 8, marginTop: 20 }}>
          <button
            type="button"
            onClick={onClose}
            style={{ ...btnSecondary, flex: 1 }}
          >
            {t('crmContactForm.cancel')}
          </button>

          <button
            type="submit"
            disabled={saving}
            style={{
              ...btnPrimary,
              flex: 1,
              opacity: saving ? 0.5 : 1,
            }}
          >
            {saving
              ? t('crmContactForm.saving')
              : isEdit
                ? t('crmContactForm.update')
                : t('crmContactForm.create')}
          </button>
        </div>
      </form>
    </div>
  );
}
