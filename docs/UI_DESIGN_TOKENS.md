# StreamVis UI Design Tokens

> 基于现代 SaaS 产品研究的设计令牌，可直接用于开发

---

## 色彩系统

### 品牌色
```css
--color-primary: #0D9488;
--color-primary-light: #14B8A6;
--color-primary-dark: #0F766E;
--color-accent: #0284C7;
```

### 中性色
```css
--color-background: #FAFAF9;
--color-panel: #FFFFFF;
--color-text: #1C1917;
--color-text-secondary: #57534E;
--color-text-muted: #A8A29E;
--color-border: #E7E5E4;
--color-border-light: #F5F5F4;
```

### 功能色
```css
--color-success: #10B981;
--color-warning: #F59E0B;
--color-error: #EF4444;
--color-info: #3B82F6;
```

### 图表色板
```css
--chart-categorical-1: #0D9488;
--chart-categorical-2: #3B82F6;
--chart-categorical-3: #F59E0B;
--chart-categorical-4: #8B5CF6;
--chart-categorical-5: #10B981;
--chart-categorical-6: #EC4899;
--chart-categorical-7: #06B6D4;
--chart-categorical-8: #F97316;
```

---

## 排版系统

### 字体
```css
--font-heading: 'JetBrains Mono', monospace;
--font-body: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
```

### 字号
```css
--text-xs: 12px;
--text-sm: 13px;
--text-base: 14px;
--text-md: 15px;
--text-lg: 16px;
--text-xl: 18px;
--text-2xl: 20px;
--text-3xl: 24px;
```

### 字重
```css
--font-normal: 400;
--font-medium: 500;
--font-semibold: 600;
--font-bold: 700;
```

### 行高
```css
--leading-tight: 1.25;
--leading-normal: 1.5;
--leading-relaxed: 1.75;
```

---

## 间距系统

```css
--space-0: 0px;
--space-1: 4px;
--space-2: 8px;
--space-3: 12px;
--space-4: 16px;
--space-5: 20px;
--space-6: 24px;
--space-8: 32px;
--space-10: 40px;
--space-12: 48px;
```

---

## 圆角系统

```css
--radius-none: 0px;
--radius-sm: 6px;
--radius-md: 10px;
--radius-lg: 14px;
--radius-xl: 16px;
--radius-2xl: 18px;
--radius-full: 9999px;
```

---

## 阴影系统

```css
--shadow-none: none;
--shadow-xs: 0 1px 2px rgba(0, 0, 0, 0.02);
--shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.04);
--shadow-md: 0 4px 6px rgba(0, 0, 0, 0.04);
--shadow-lg: 0 10px 15px rgba(0, 0, 0, 0.04);
--shadow-xl: 0 20px 25px rgba(0, 0, 0, 0.04);

/* 彩色阴影（用于按钮悬浮） */
--shadow-primary: 0 4px 12px rgba(13, 148, 136, 0.25);
```

---

## 动效系统

### 时长
```css
--duration-instant: 0ms;
--duration-fast: 100ms;
--duration-normal: 150ms;
--duration-slow: 250ms;
--duration-slower: 350ms;
```

### 缓动函数
```css
--ease-linear: linear;
--ease-in: cubic-bezier(0.4, 0, 1, 1);
--ease-out: cubic-bezier(0, 0, 0.2, 1);
--ease-in-out: cubic-bezier(0.4, 0, 0.2, 1);
--ease-spring: cubic-bezier(0.2, 0, 0.2, 1);
```

---

## 布局参数

```css
/* 侧边栏 */
--sidebar-width: 260px;
--sidebar-width-collapsed: 60px;

/* 内容区 */
--content-max-width: 900px;
--content-padding: 24px;

/* 顶部栏 */
--header-height: 56px;

/* 输入区 */
--input-area-height: auto;
--input-min-height: 48px;
```

---

## Z-Index 层级

```css
--z-base: 0;
--z-dropdown: 100;
--z-sticky: 200;
--z-fixed: 300;
--z-modal-backdrop: 400;
--z-modal: 500;
--z-popover: 600;
--z-tooltip: 700;
```

---

## 组件规范

### 按钮

```css
/* 主要按钮 */
.btn-primary {
  background: var(--color-primary);
  color: white;
  padding: 10px 20px;
  border-radius: var(--radius-md);
  font-weight: var(--font-medium);
  font-size: var(--text-sm);
  border: none;
  box-shadow: var(--shadow-sm);
  transition: all var(--duration-normal) var(--ease-in-out);
}

.btn-primary:hover {
  background: var(--color-primary-dark);
  box-shadow: var(--shadow-primary);
  transform: translateY(-1px);
}

/* 次要按钮 */
.btn-secondary {
  background: var(--color-panel);
  color: var(--color-text-secondary);
  border: 1px solid var(--color-border);
  padding: 10px 20px;
  border-radius: var(--radius-md);
  font-weight: var(--font-medium);
  font-size: var(--text-sm);
  transition: all var(--duration-normal) var(--ease-in-out);
}

.btn-secondary:hover {
  background: var(--color-background);
  border-color: var(--color-text-muted);
  color: var(--color-text);
}
```

### 输入框

```css
.input {
  height: 48px;
  padding: 0 16px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: var(--text-md);
  background: var(--color-panel);
  color: var(--color-text);
  transition: all var(--duration-normal) var(--ease-in-out);
}

.input:hover {
  border-color: var(--color-text-muted);
}

.input:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(13, 148, 136, 0.08);
  outline: none;
}
```

### 卡片

```css
.card {
  background: var(--color-panel);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-5);
  box-shadow: var(--shadow-sm);
  transition: all var(--duration-normal) var(--ease-in-out);
}

.card:hover {
  box-shadow: var(--shadow-md);
}
```

### 消息气泡

```css
/* 用户消息 */
.message-user {
  background: #F0EFEA;
  color: var(--color-text);
  border-radius: var(--radius-xl);
  border-bottom-right-radius: var(--radius-sm);
  padding: 14px 18px;
  max-width: 85%;
  margin-left: auto;
  box-shadow: var(--shadow-xs);
}

/* AI消息 */
.message-assistant {
  background: var(--color-panel);
  color: var(--color-text);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  border-bottom-left-radius: var(--radius-sm);
  padding: 14px 18px;
  max-width: 90%;
  box-shadow: var(--shadow-xs);
}
```

### 图表容器

```css
.chart-container {
  background: var(--color-panel);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-5);
  margin: var(--space-3) 0;
  box-shadow: var(--shadow-sm);
  transition: all var(--duration-normal) var(--ease-in-out);
}

.chart-container:hover {
  box-shadow: var(--shadow-md);
}

.chart-title {
  font-family: var(--font-heading);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: var(--space-3);
}
```

---

## 动画关键帧

```css
/* 消息出现 */
@keyframes messageAppear {
  from {
    opacity: 0;
    transform: translateY(12px) scale(0.98);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

/* 图表出现 */
@keyframes chartAppear {
  from {
    opacity: 0;
    transform: scale(0.96);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

/* 思考动画 */
@keyframes thinkingPulse {
  0%, 100% { opacity: 0.4; transform: scale(0.8); }
  50% { opacity: 1; transform: scale(1); }
}

/* 脉冲效果 */
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* 旋转 */
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
```

---

## 响应式断点

```css
--breakpoint-sm: 640px;
--breakpoint-md: 768px;
--breakpoint-lg: 1024px;
--breakpoint-xl: 1280px;
--breakpoint-2xl: 1536px;
```
