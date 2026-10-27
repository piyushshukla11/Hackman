# PRISM Design System: Forensic Prism

> **"White light in, split into coloured spectral beams per feature."**  
> *A high-precision, dark-mode, forensic aesthetic designed for diagnosis, not passive summaries.*

---

## 1. Aesthetic Vision & Core Tenets

1. **Forensic Optical Metaphor**: Review data starts as raw, uncalibrated white light. As it passes through PRISM's computational prism (trust cascade, language normalization, semantic embedding), noise and bots are filtered out, and the stream refracts into clean, distinct spectral beams corresponding to product features.
2. **Ultra-Dark Chromatic Canvas**: Surfaces avoid flat grays in favor of deep obsidian and midnight blue tones (`#06080e`, `#0a0e1a`, `#111827`) that maximize contrast for bright spectral accents.
3. **Glassmorphism with Discipline**: Panels utilize ultra-subtle backdrop blurs (`backdrop-blur-md`) with semi-transparent borders (`rgba(255, 255, 255, 0.07)`). No heavy drop shadows or decorative clutter.
4. **Motion with Intent**: No looping decorative animations. Micro-animations occur solely to communicate state transitions, data ingress, quarantine rejections, or statistical confidence shifts.

---

## 2. Color Palette & Spectral Tokens

### A. Base Surfaces
| Token | Hex Value | Usage |
| :-- | :-- | :-- |
| `bg-canvas` | `#06080e` | Deep background canvas |
| `bg-surface` | `#0b101d` | Card and panel container surface |
| `bg-surface-elevated` | `#121a2d` | Hover states, modals, popovers |
| `border-subtle` | `rgba(255, 255, 255, 0.08)` | Standard panel outline |
| `border-highlight` | `rgba(255, 255, 255, 0.20)` | Active, focused, or selected borders |

### B. Spectral Feature Beams
Every product feature is permanently associated with a specific wavelength in the PRISM spectrum. This color remains consistent across the entire app:

| Feature Name | Token | Hex | Optical Hue |
| :-- | :-- | :-- | :-- |
| **Battery Life & Power** | `beam-cyan` | `#06b6d4` | Laser Cyan |
| **Packaging & Delivery** | `beam-amber` | `#f59e0b` | High-vis Amber |
| **Build Quality & Durability**| `beam-blue` | `#3b82f6` | Cobalt Blue |
| **Audio / Performance** | `beam-purple`| `#a855f7` | Ultraviolet Purple |
| **Customer Support & Service**| `beam-emerald`| `#10b981` | Neon Emerald |
| **Connectivity & Software** | `beam-indigo`| `#6366f1` | Deep Violet / Indigo |
| **Value for Money** | `beam-rose` | `#f43f5e` | Crimson Rose |

### C. Diagnostic & Confidence Indicators
Confidence tiers and verdict states use unambiguous status colors:

| Status Tier | Color Hex | Label | Meaning |
| :-- | :-- | :-- | :-- |
| **High Confidence / Act** | `#22c55e` | Green | Confidence $\ge 0.75$. Root cause verified; immediate action warranted. |
| **Medium / Monitor** | `#eab308` | Amber/Yellow | Confidence $0.45 - 0.74$. Pattern emerging; actively monitor or survey. |
| **Low / Gather Data** | `#ef4444` | Red | Confidence $< 0.45$. Insufficient evidence or conflicting signals. |
| **Quarantined / Bot** | `#94a3b8` | Slate Muted | Failed trust gate; excluded or downweighted. |

---

## 3. Typography Hierarchy

PRISM utilizes modern geometric sans-serif fonts paired with tabular monospaced numbers for scientific readability:

* **Primary Body & Interface**: `Inter, system-ui, -apple-system, sans-serif`
* **Display & Hero Accents**: `Orbitron, "Space Grotesk", sans-serif` (Reserved for the PRISM title, stage numbers, and signature visual headings)
* **Metrics & Code Data**: `JetBrains Mono, Fira Code, monospace` (Used for hashes, confidence scores, p-values, batch codes, and timestamps)

### Type Scale
| Level | Size | Weight | Line Height | Usage |
| :-- | :-- | :-- | :-- | :-- |
| `text-display` | 48px - 64px | 800 (Bold) | 1.1 | Health score badge, Hero titles |
| `text-h1` | 24px - 32px | 700 (Bold) | 1.2 | Page titles (`Prism Stream`, `Review X-Ray`) |
| `text-h2` | 18px - 20px | 600 (Semibold)| 1.3 | Card headers, Modal titles |
| `text-body` | 14px | 400 (Regular) | 1.5 | General text, review snippets, table cells |
| `text-caption` | 12px | 500 (Medium)  | 1.4 | Timestamps, tags, reason codes, sample sizes |
| `text-mono` | 13px | 400 (Regular) | 1.4 | `B-0716`, `p < 0.01`, `sha256:...` |

---

## 4. UI Components & Tokens

### A. Forensic Cards
```css
.prism-card {
  background: rgba(11, 16, 29, 0.75);
  border: 1px solid rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(12px);
  border-radius: 12px;
  transition: border-color 0.2s ease, transform 0.2s ease;
}
.prism-card:hover {
  border-color: rgba(255, 255, 255, 0.16);
  transform: translateY(-1px);
}
```

### B. Confidence Meter Pill
Displays the current confidence score alongside its color tier and confidence interval:
- High: Green border, subtle green glow.
- Monitor: Amber border.
- Low: Red border, alert pulse.

### C. Trust & Quarantine Toggle Bar
A top-bar element that always discloses:
`Analyzed: 1,482 reviews | Quarantined: 138 (9.3%) | [ Toggle: Show Quarantined ]`
Toggling this dynamically recalculates and animates dashboard metrics between clean-only and complete dataset views.

---

## 5. Motion & Interaction Rules

1. **Spring Physics**: Framer Motion transitions use natural spring physics (`type: 'spring', damping: 25, stiffness: 200`) rather than linear easings.
2. **Event-Driven Visual Reactions**:
   - When a review passes Stage 2 (Trust), it pulses white into the canvas.
   - When a review fails Trust, it sparks and deflects downwards into the quarantine tray.
   - When a verification survey response arrives via SSE, the confidence bar visibly shifts and turns green if threshold is crossed.
3. **Reduced Motion Compliance**:
   All CSS and Framer Motion elements respect `prefers-reduced-motion: reduce`, dropping canvas physics and complex spring transforms in favor of immediate opacity fades.
