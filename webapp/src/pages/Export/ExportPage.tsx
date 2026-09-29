import { useState } from 'react';
import { getAccessToken } from '../../shared/api/auth';
import { t } from '../../shared/i18n';
import { Card, ListItem, PrimaryButton, SectionHeader, SubScreen } from '../../shared/ui';

type Format = 'csv' | 'xlsx';

function currentMonth(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
}

export function ExportPage() {
  const [month, setMonth] = useState(currentMonth());
  const [format, setFormat] = useState<Format>('xlsx');
  const [state, setState] = useState<'idle' | 'loading' | 'error'>('idle');

  async function download() {
    setState('loading');
    try {
      const base = import.meta.env.VITE_API_BASE_URL ?? '';
      const token = await getAccessToken();
      const res = await fetch(
        `${base}/api/v1/export/transactions?format=${format}&month=${month}-01`,
        { headers: { Authorization: `Bearer ${token}` } },
      );
      if (!res.ok) throw new Error(`${res.status}`);

      // The export endpoint requires a Bearer token, so Telegram's native
      // downloadFile() (which the Telegram client fetches itself, with no
      // way to attach our header) can't be used — fetch the blob ourselves
      // and hand it to the browser via a temporary object URL instead.
      const blob = await res.blob();
      const disposition = res.headers.get('content-disposition') ?? '';
      const filename = /filename="?([^"]+)"?/.exec(disposition)?.[1] ?? `transactions.${format}`;
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
      setState('idle');
    } catch {
      setState('error');
    }
  }

  return (
    <SubScreen title={t.more.export}>
      <SectionHeader>Экспорт транзакций</SectionHeader>
      <Card padding="4px 0">
        <ListItem
          border={false}
          left={<div style={{ fontSize: 15, padding: '0 12px' }}>Месяц</div>}
          right={
            <input
              type="month"
              value={month}
              onChange={(e) => setMonth(e.target.value)}
              style={{
                border: 'none',
                background: 'none',
                color: 'var(--color-link)',
                fontWeight: 600,
                fontSize: 15,
                marginRight: 12,
              }}
            />
          }
        />
      </Card>
      <Card padding="4px 0">
        {(['csv', 'xlsx'] as const).map((f, i) => (
          <ListItem
            key={f}
            border={i === 0}
            onClick={() => setFormat(f)}
            left={
              <div style={{ padding: '0 12px' }}>
                <div style={{ fontSize: 15 }}>{f === 'csv' ? 'CSV' : 'Excel (.xlsx)'}</div>
                <div style={{ fontSize: 12, color: 'var(--color-hint)' }}>
                  {f === 'csv' ? 'Открывается в Excel, Google Sheets' : 'С форматированием и итогами'}
                </div>
              </div>
            }
            right={
              <div
                style={{
                  width: 20,
                  height: 20,
                  borderRadius: 10,
                  marginRight: 12,
                  border: `2px solid ${format === f ? 'var(--color-link)' : 'var(--color-separator)'}`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                {format === f && (
                  <div style={{ width: 10, height: 10, borderRadius: 5, background: 'var(--color-link)' }} />
                )}
              </div>
            }
          />
        ))}
      </Card>
      <PrimaryButton onClick={download}>
        {state === 'loading' ? t.common.loading : 'Скачать'}
      </PrimaryButton>
      {state === 'error' && (
        <div style={{ color: 'var(--color-destructive)', fontSize: 13, textAlign: 'center' }}>
          Не удалось скачать файл
        </div>
      )}
    </SubScreen>
  );
}
