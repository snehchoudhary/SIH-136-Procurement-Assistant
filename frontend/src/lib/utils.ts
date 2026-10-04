/**
 * Merges class names, filtering out falsy values.
 * Lightweight alternative to clsx for simple cases.
 */
export function cn(...classes: Array<string | undefined | false | null>): string {
  return classes.filter(Boolean).join(' ');
}
