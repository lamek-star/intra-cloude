/**
 * The shop's own details for what IntraForge prints: its name on every label, and its name, address, phone, tax number,
 * currency and closing note on every invoice. Kept per business app on this browser (each counter PC fills them in
 * once); nothing here is sensitive, and the app's records stay the only source of what was sold.
 */
export type ShopDetails = {
  name: string;
  address: string;
  phone: string;
  taxId: string;
  currency: string;
  footer: string;
};

const key = (instanceId: string) => `intraforge.shop-details.${instanceId}`;

export function defaultShopDetails(appLabel: string): ShopDetails {
  return { name: appLabel, address: "", phone: "", taxId: "", currency: "", footer: "Thank you for your business." };
}

export function loadShopDetails(instanceId: string, appLabel: string): ShopDetails {
  const fallback = defaultShopDetails(appLabel);
  try {
    const raw = typeof window === "undefined" ? null : window.localStorage.getItem(key(instanceId));
    if (!raw) return fallback;
    const saved = JSON.parse(raw) as Partial<ShopDetails>;
    const pick = (k: keyof ShopDetails) => (typeof saved[k] === "string" ? (saved[k] as string).slice(0, 300) : fallback[k]);
    return { name: pick("name"), address: pick("address"), phone: pick("phone"), taxId: pick("taxId"), currency: pick("currency"), footer: pick("footer") };
  } catch {
    return fallback;
  }
}

export function saveShopDetails(instanceId: string, details: ShopDetails) {
  try {
    window.localStorage.setItem(key(instanceId), JSON.stringify(details));
  } catch {
    /* private window or blocked storage: the details apply to this print only */
  }
}

/** "120.00 ERN" when the shop set a currency, else "120.00". */
export function withCurrency(amount: string, currency: string): string {
  return currency.trim() ? `${amount} ${currency.trim()}` : amount;
}
