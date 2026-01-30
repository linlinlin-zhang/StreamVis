# Design System Master File

> **LOGIC:** When building a specific page, first check `design-system/pages/[page-name].md`.
> If that file exists, its rules **override** this Master file.
> If not, strictly follow the rules below.

---

**Project:** StreamVis
**Generated:** 2026-01-30
**Category:** AI Data Visualization Dashboard

---

## Global Rules

### Color Palette - Light Theme

| Role | Hex | CSS Variable |
|------|-----|--------------|
| Primary | `#0d9488` | `--color-primary` |
| Primary Light | `#14b8a6` | `--color-primary-light` |
| Primary Dark | `#0f766e` | `--color-primary-dark` |
| Accent | `#0284c7` | `--color-accent` |
| Background | `#fafaf9` | `--color-background` |
| Panel | `#ffffff` | `--color-panel` |
| Text | `#1c1917` | `--color-text` |
| Text Secondary | `#57534e` | `--color-text-secondary` |
| Text Muted | `#a8a29e` | `--color-text-muted` |
| Border | `#e7e5e4` | `--color-border` |

**Color Philosophy:** 
- 清新明亮的青绿色作为主色调，传达专业与可信赖感
- 温暖的灰白色背景，长时间使用不易疲劳
- 深灰色文字确保最佳可读性

### Typography

- **Heading Font:** JetBrains Mono (monospace)
- **Body Font:** Inter (sans-serif)
- **Mood:** Modern, clean, technical, professional
- **Google Fonts:** [Inter + JetBrains Mono](https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap)

**CSS Import:**
```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');
```

### Spacing Variables

| Token | Value | Usage |
|-------|-------|-------|
| `--space-xs` | `4px` | Tight gaps |
| `--space-sm` | `8px` | Icon gaps |
| `--space-md` | `12px` | Standard padding |
| `--space-lg` | `16px` | Section padding |
| `--space-xl` | `24px` | Large gaps |
| `--space-2xl` | `32px` | Section margins |

### Shadow Depths

| Level | Value | Usage |
|-------|-------|-------|
| `--shadow-xs` | `0 1px 2px rgba(0,0,0,0.02)` | Subtle lift |
| `--shadow-sm` | `0 1px 3px rgba(0,0,0,0.04)` | Cards, buttons |
| `--shadow-md` | `0 4px 6px rgba(0,0,0,0.04)` | Elevated cards |
| `--shadow-lg` | `0 10px 15px rgba(0,0,0,0.04)` | Modals, dropdowns |
| `--shadow-xl` | `0 20px 25px rgba(0,0,0,0.04)` | Overlays |

### Border Radius

| Token | Value | Usage |
|-------|-------|-------|
| `--radius-sm` | `6px` | Small elements |
| `--radius-md` | `10px` | Buttons, inputs |
| `--radius-lg` | `14px` | Cards, panels |
| `--radius-xl` | `18px` | Modals |
| `--radius-full` | `9999px` | Pills, avatars |

---

## Component Specs

### Buttons

```css
/* Primary Button */
.btn-primary {
  background: #0d9488;
  color: white;
  padding: 8px 16px;
  border-radius: 10px;
  font-weight: 500;
  font-size: 13px;
  border: 1px solid #0d9488;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
  transition: all 150ms ease;
}

.btn-primary:hover {
  background: #0f766e;
  border-color: #0f766e;
  box-shadow: 0 4px 6px rgba(0,0,0,0.04);
}

/* Secondary Button */
.btn-secondary {
  background: #ffffff;
  color: #57534e;
  border: 1px solid #e7e5e4;
  padding: 8px 16px;
  border-radius: 10px;
  font-weight: 500;
  font-size: 13px;
  transition: all 150ms ease;
}

.btn-secondary:hover {
  background: #f5f5f4;
  border-color: #a8a29e;
  color: #1c1917;
}
```

### Cards / Panels

```css
.panel {
  background: #ffffff;
  border-radius: 14px;
  border: 1px solid #e7e5e4;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
  overflow: hidden;
}
```

### Inputs

```css
.input {
  height: 40px;
  padding: 0 12px;
  border: 1px solid #e7e5e4;
  border-radius: 10px;
  font-size: 14px;
  background: #ffffff;
  color: #1c1917;
  transition: all 150ms ease;
}

.input:hover {
  border-color: #a8a29e;
}

.input:focus {
  border-color: #0d9488;
  box-shadow: 0 0 0 3px rgba(13, 148, 136, 0.08);
  outline: none;
}
```

### Message Bubbles

```css
/* User Message */
.message-user {
  background: #0d9488;
  color: white;
  border-radius: 14px;
  border-bottom-right-radius: 6px;
  padding: 12px 16px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}

/* Assistant Message */
.message-assistant {
  background: #f5f5f4;
  color: #1c1917;
  border: 1px solid #e7e5e4;
  border-radius: 14px;
  border-bottom-left-radius: 6px;
  padding: 12px 16px;
}

/* System Message */
.message-system {
  background: rgba(2, 132, 199, 0.08);
  border: 1px solid rgba(2, 132, 199, 0.15);
  color: #0284c7;
  border-radius: 9999px;
  padding: 6px 12px;
  font-size: 12px;
  font-weight: 500;
}
```

### Modals

```css
.modal-overlay {
  background: rgba(0, 0, 0, 0.35);
  backdrop-filter: blur(4px);
}

.modal {
  background: #ffffff;
  border-radius: 18px;
  border: 1px solid #e7e5e4;
  padding: 0;
  box-shadow: 0 20px 25px rgba(0, 0, 0, 0.08);
  max-width: 520px;
  width: 90%;
  overflow: hidden;
}

.modal-header {
  padding: 16px 20px;
  border-bottom: 1px solid #e7e5e4;
}

.modal-body {
  padding: 20px;
}
```

### Charts

```css
/* Graph Nodes */
.node-circle {
  fill: #0d9488;
  stroke: #ffffff;
  stroke-width: 2;
  filter: drop-shadow(0 2px 3px rgba(0,0,0,0.1));
}

.node-text {
  fill: #57534e;
  font-size: 12px;
  font-weight: 500;
}

.link-line {
  stroke: #d6d3d1;
  stroke-width: 2;
}

/* Plot Chart */
.plot-line {
  stroke: #0d9488;
  stroke-width: 2.5;
  fill: none;
}

.plot-area {
  fill: rgba(13, 148, 136, 0.1);
}

.plot-dot {
  fill: #0d9488;
  stroke: #ffffff;
  stroke-width: 2;
}

.plot-bar {
  fill: #0d9488;
  rx: 4;
}

.axis-text {
  fill: #57534e;
  font-size: 12px;
}

.grid-line {
  stroke: #e7e5e4;
  stroke-dasharray: 3,3;
}
```

---

## Style Guidelines

**Style:** Light Mode (Modern Clean)

**Keywords:** Light theme, clean, minimal, professional, friendly, approachable, modern, spacious

**Best For:** Daytime use, professional applications, data visualization, collaborative tools

**Key Effects:** 
- Subtle shadows for depth
- Rounded corners for friendliness
- Clear visual hierarchy
- Generous whitespace
- Smooth transitions (150ms)

---

## Anti-Patterns (Do NOT Use)

- ❌ Dark mode default
- ❌ Pure white background (use warm off-white #fafaf9)
- ❌ Pure black text (use warm dark #1c1917)
- ❌ Harsh shadows (use subtle, diffused shadows)
- ❌ Sharp corners on interactive elements
- ❌ Instant state changes (always use 150ms transitions)
- ❌ Missing focus states
- ❌ Emojis as icons — Use Lucide icons
- ❌ Missing cursor:pointer — All clickable elements must have cursor:pointer
- ❌ Low contrast text — Maintain 4.5:1 minimum contrast ratio

---

## Pre-Delivery Checklist

Before delivering any UI code, verify:

- [ ] No emojis used as icons (use Lucide instead)
- [ ] All icons from consistent icon set (Lucide)
- [ ] `cursor-pointer` on all clickable elements
- [ ] Hover states with smooth transitions (150ms)
- [ ] Light mode: text contrast 4.5:1 minimum
- [ ] Focus states visible for keyboard navigation
- [ ] `prefers-reduced-motion` respected
- [ ] Responsive: 375px, 768px, 1024px, 1440px
- [ ] No content hidden behind fixed navbars
- [ ] No horizontal scroll on mobile
