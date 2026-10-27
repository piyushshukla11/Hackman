/** Mirrors simulation/seed-reviews.json products for display names */
export const PRODUCTS = [
  { product_id: 'prod_001', name: 'Voyage Horizon ANC', emoji: '' },
  { product_id: 'prod_002', name: 'Voyage StreamCast Pro', emoji: '' },
  { product_id: 'prod_003', name: 'Voyage Apex Wireless', emoji: '' },
  { product_id: 'prod_004', name: 'Voyage UltraVision 27"', emoji: '' },
];

export function productNameMap() {
  return Object.fromEntries(PRODUCTS.map((p) => [p.product_id, p.name]));
}
