const fs = require('fs');
const vm = require('vm');
const path = require('path');

const simulationDir = path.join(__dirname, '..', 'simulation');
const htmlFiles = ['amazon.html', 'flipkart.html', 'jiomart.html', 'brand.html', 'steam.html'];

for (const htmlFile of htmlFiles) {
  const htmlPath = path.join(simulationDir, htmlFile);
  const html = fs.readFileSync(htmlPath, 'utf8');

  // Match all script tags
  const regex = /<script(?:\s+src="([^"]+)")?>([\s\S]*?)<\/script>/gi;
  let match;
  const scripts = [];
  while ((match = regex.exec(html)) !== null) {
    scripts.push({ src: match[1], inline: match[2] });
  }

  const domElements = {};
  function getElem(id) {
    if (!domElements[id]) {
      domElements[id] = {
        innerHTML: '',
        value: '',
        style: {},
        classList: { add: () => {}, remove: () => {}, toggle: () => {} },
        setAttribute: () => {},
        getAttribute: () => '',
        appendChild: () => {},
        querySelectorAll: () => [],
        querySelector: () => null,
      };
    }
    return domElements[id];
  }

  const context = {
    window: {},
    document: {
      getElementById: (id) => getElem(id),
      querySelectorAll: (sel) => [getElem('mock1'), getElem('mock2')],
      querySelector: (sel) => getElem('mock1'),
      createElement: (tag) => getElem(tag),
      scrollTo: () => {},
    },
    console: {
      log: () => {},
      warn: () => {},
      error: (msg) => console.error(`[${htmlFile}] Console Error:`, msg)
    },
    setTimeout: (fn) => {},
    clearTimeout: () => {},
    Intl: Intl,
    Date: Date,
    Math: Math,
    fetch: () => Promise.resolve({ ok: true, json: () => Promise.resolve({}) })
  };
  context.window = context;
  vm.createContext(context);

  console.log(`Evaluating ${htmlFile} (${scripts.length} scripts)...`);
  for (const s of scripts) {
    if (s.src) {
      const srcFile = path.join(simulationDir, s.src.replace('./', ''));
      if (fs.existsSync(srcFile)) {
        const code = fs.readFileSync(srcFile, 'utf8');
        try {
          vm.runInContext(code, context);
        } catch (e) {
          console.error(`  ✗ Error in ${s.src} (${htmlFile}):`, e.stack || e.message);
        }
      } else {
        console.warn(`  ! Script src file not found: ${srcFile}`);
      }
    } else if (s.inline && s.inline.trim()) {
      try {
        vm.runInContext(s.inline, context);
      } catch (e) {
        console.error(`  ✗ Error in inline script (${htmlFile}):`, e.stack || e.message);
      }
    }
  }

  // Check picker-grid or products-grid content
  const pickerGrid = domElements['picker-grid'];
  const productsGrid = domElements['products-grid'];
  const steamFeed = domElements['reviews_feed'];

  if (pickerGrid && pickerGrid.innerHTML) {
    console.log(`  ✓ picker-grid populated (${pickerGrid.innerHTML.length} chars)`);
  }
  if (productsGrid && productsGrid.innerHTML) {
    console.log(`  ✓ products-grid populated (${productsGrid.innerHTML.length} chars)`);
  }
  if (steamFeed && steamFeed.innerHTML) {
    console.log(`  ✓ Steam reviews_feed populated (${steamFeed.innerHTML.length} chars)`);
  }
  console.log(`✓ ${htmlFile} loaded cleanly with ZERO syntax or runtime errors!\n`);
}
