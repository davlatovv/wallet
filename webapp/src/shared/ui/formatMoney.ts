/**
 * The API always sends money as a decimal string with exactly 2 decimals
 * (see app/presentation/api/schemas/common.py MoneyStr) — never a float, so
 * this never routes a value through JS floating point.
 */
export function formatMoney(value: string, { showDecimals = false } = {}): string {
  const negative = value.startsWith('-');
  const abs = negative ? value.slice(1) : value;
  const [whole, decimals] = abs.split('.');
  const grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
  const suffix = showDecimals && decimals ? `,${decimals}` : '';
  return `${negative ? '−' : ''}${grouped}${suffix}`;
}
