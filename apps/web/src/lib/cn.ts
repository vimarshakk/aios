export type ClassValue = string | number | null | false | undefined | ClassValue[];

/**
 * Tiny classnames helper. Joins truthy values with spaces.
 */
export function cn(...values: ClassValue[]): string {
  const out: string[] = [];
  for (const v of values) {
    if (!v) continue;
    if (Array.isArray(v)) {
      const nested = cn(...v);
      if (nested) out.push(nested);
    } else {
      out.push(String(v));
    }
  }
  return out.join(" ");
}

export default cn;
