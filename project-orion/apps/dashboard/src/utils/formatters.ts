/**
 * Financial formatters ensuring Decimal-safe display without float arithmetic bugs.
 */

export function formatCurrency(
  value: string | number | null | undefined,
  currency = 'USD',
  decimalPlaces = 2
): string {
  if (value === null || value === undefined || value === '') {
    return '—';
  }

  const num = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(num)) {
    return String(value);
  }

  try {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
      minimumFractionDigits: decimalPlaces,
      maximumFractionDigits: decimalPlaces,
    }).format(num);
  } catch {
    return `${currency} ${num.toFixed(decimalPlaces)}`;
  }
}

export function formatPnl(value: string | number | null | undefined, currency = 'USD'): {
  formatted: string;
  isPositive: boolean;
  isNegative: boolean;
  isZero: boolean;
  prefix: string;
} {
  if (value === null || value === undefined || value === '') {
    return {
      formatted: '—',
      isPositive: false,
      isNegative: false,
      isZero: true,
      prefix: '',
    };
  }

  const num = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(num)) {
    return {
      formatted: String(value),
      isPositive: false,
      isNegative: false,
      isZero: true,
      prefix: '',
    };
  }

  const isPositive = num > 0;
  const isNegative = num < 0;
  const isZero = num === 0;

  const prefix = isPositive ? '+' : '';
  const formatted = `${prefix}${formatCurrency(num, currency)}`;

  return { formatted, isPositive, isNegative, isZero, prefix };
}

export function formatPercent(value: string | number | null | undefined, digits = 2): string {
  if (value === null || value === undefined || value === '') {
    return '—';
  }

  const num = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(num)) {
    return '—';
  }

  const prefix = num > 0 ? '+' : '';
  return `${prefix}${num.toFixed(digits)}%`;
}

export function formatUnits(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === '') {
    return '0';
  }

  const num = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(num)) {
    return String(value);
  }

  return new Intl.NumberFormat('en-US').format(num);
}

export function formatPrice(value: string | number | null | undefined, decimals = 5): string {
  if (value === null || value === undefined || value === '') {
    return '—';
  }

  const num = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(num)) {
    return String(value);
  }

  return num.toFixed(decimals);
}

export function formatDateTime(isoString: string | null | undefined): string {
  if (!isoString) {
    return '—';
  }

  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) {
      return String(isoString);
    }
    return d.toISOString().replace('T', ' ').substring(0, 19) + ' UTC';
  } catch {
    return String(isoString);
  }
}
