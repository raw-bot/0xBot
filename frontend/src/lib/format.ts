/**
 * Formatting utilities for currency and percentage display
 */

/**
 * Format a number as money with optional decimal places
 */
export function formatMoney(value: number, decimals: number = 2): string {
  return value.toFixed(decimals);
}

/**
 * Format a percentage with sign prefix (+/-)
 */
export function formatSignedPercent(value: number): string {
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}%`;
}

/**
 * Format money with sign prefix (+/-)
 */
export function formatSignedMoney(value: number): string {
  const sign = value >= 0 ? '+' : '';
  return `${sign}$${value.toFixed(2)}`;
}
