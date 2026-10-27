/**
 * Product display names for pipeline / surveys / dashboard (matches simulation seed-data).
 */
const NAMES = {
  prod_001: 'Voyage Horizon ANC',
  prod_002: 'Voyage StreamCast Pro',
  prod_003: 'Voyage Apex Wireless',
  prod_004: 'Voyage UltraVision 27"',
  'prod-001': 'Voyage Horizon ANC',
  steam_games: 'Voyage Steam Gaming Suite',
};

function getProductName(productId) {
  if (!productId) return 'Voyage Product';
  return NAMES[productId] || NAMES[productId.replace('-', '_')] || productId.replace(/_/g, ' ');
}

module.exports = { getProductName, NAMES };
