export const FEATURE_ORDER = [
  'performance',
  'battery_life',
  'build_quality',
  'value_for_money',
  'customer_support',
  'delivery_speed',
  'packaging',
];

export const FEATURE_LABELS = {
  performance: 'Performance',
  battery_life: 'Battery Life',
  build_quality: 'Build Quality',
  value_for_money: 'Value for Money',
  customer_support: 'Customer Support',
  delivery_speed: 'Delivery Speed',
  packaging: 'Packaging',
};

// Refined modern status colors for graph visualization
export const FEATURE_COLORS = {
  performance: '#38bdf8',      // Sky
  battery_life: '#a78bfa',     // Violet
  build_quality: '#f472b6',    // Soft Pink
  value_for_money: '#f59e0b',  // Warm Amber
  customer_support: '#2dd4bf', // Mint Teal
  delivery_speed: '#fb923c',   // Tangerine
  packaging: '#14b8a6',        // Deep Teal
};

export function labelFeature(key) {
  return FEATURE_LABELS[key] || key?.replace(/_/g, ' ') || 'General';
}
