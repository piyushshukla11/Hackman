// seed-data.js — Product catalog for PRISM simulation pages.
// Brand: Voyage | Products: Monitor, Mouse, Headphones, Mic
// Exposes window.SEED_DATA and global SEED_DATA

(function() {
  const data = {
    "company": "Voyage",
    "products": [
      {
        "product_id": "prod_001",
        "name": "Voyage Horizon ANC",
        "category": "Headphones",
        "description": "Wireless studio headphones with 45dB hybrid ANC, 40mm beryllium drivers, BT 5.4, 50hr battery, LDAC Hi-Res audio, ultra-plush memory foam.",
        "price": 5999,
        "mrp": 9999,
        "platform_prices": { "amazon": 5999, "flipkart": 5699, "jiomart": 6199, "brand": 5499 },
        "emoji": "🎧",
        "images": {
          "amazon": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=600&h=400&fit=crop",
          "flipkart": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=600&h=400&fit=crop",
          "jiomart": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=600&h=400&fit=crop",
          "brand": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=600&h=400&fit=crop"
        }
      },
      {
        "product_id": "prod_002",
        "name": "Voyage StreamCast Pro",
        "category": "Microphones",
        "description": "Professional USB condenser microphone with cardioid/omni patterns, 192kHz/24-bit resolution, zero-latency monitoring, internal shockmount & pop filter.",
        "price": 4499,
        "mrp": 7999,
        "platform_prices": { "amazon": 4499, "flipkart": 4199, "jiomart": 4699, "brand": 3999 },
        "emoji": "🎙️",
        "images": {
          "amazon": "https://images.unsplash.com/photo-1590658268037-6bf12165a8df?w=600&h=400&fit=crop",
          "flipkart": "https://images.unsplash.com/photo-1590658268037-6bf12165a8df?w=600&h=400&fit=crop",
          "jiomart": "https://images.unsplash.com/photo-1590658268037-6bf12165a8df?w=600&h=400&fit=crop",
          "brand": "https://images.unsplash.com/photo-1590658268037-6bf12165a8df?w=600&h=400&fit=crop"
        }
      },
      {
        "product_id": "prod_003",
        "name": "Voyage Apex Wireless",
        "category": "Gaming Mouse",
        "description": "Ultralight 58g wireless gaming mouse with 26,000 DPI optical sensor, optical switches, 1000Hz polling rate, pure PTFE glides, 90hr battery.",
        "price": 3499,
        "mrp": 5999,
        "platform_prices": { "amazon": 3499, "flipkart": 3299, "jiomart": 3599, "brand": 2999 },
        "emoji": "🖱️",
        "images": {
          "amazon": "https://images.unsplash.com/photo-1615663245857-ac93bb7c39e7?w=600&h=400&fit=crop",
          "flipkart": "https://images.unsplash.com/photo-1615663245857-ac93bb7c39e7?w=600&h=400&fit=crop",
          "jiomart": "https://images.unsplash.com/photo-1615663245857-ac93bb7c39e7?w=600&h=400&fit=crop",
          "brand": "https://images.unsplash.com/photo-1615663245857-ac93bb7c39e7?w=600&h=400&fit=crop"
        }
      },
      {
        "product_id": "prod_004",
        "name": "Voyage UltraVision 27\"",
        "category": "Gaming Monitors",
        "description": "27\" Fast IPS QHD 165Hz 1ms gaming monitor, HDR400, AMD FreeSync Premium, 99% sRGB, USB-C 65W PD, height & pivot adjustable stand.",
        "price": 18999,
        "mrp": 28999,
        "platform_prices": { "amazon": 18999, "flipkart": 18499, "jiomart": 19499, "brand": 17999 },
        "emoji": "🖥️",
        "images": {
          "amazon": "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=600&h=400&fit=crop",
          "flipkart": "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=600&h=400&fit=crop",
          "jiomart": "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=600&h=400&fit=crop",
          "brand": "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=600&h=400&fit=crop"
        }
      }
    ],
    "reviews": []
  };

  if (typeof window !== 'undefined') {
    window.SEED_DATA = data;
  }
  if (typeof global !== 'undefined') {
    global.SEED_DATA = data;
  }
})();
var SEED_DATA = (typeof window !== 'undefined' ? window.SEED_DATA : (typeof global !== 'undefined' ? global.SEED_DATA : null));
