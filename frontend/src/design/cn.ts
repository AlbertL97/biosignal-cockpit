// Tiny className helper (re-export of clsx) so design + app code share one import.
import clsx, { type ClassValue } from "clsx";

export function cn(...inputs: ClassValue[]): string {
  return clsx(inputs);
}
