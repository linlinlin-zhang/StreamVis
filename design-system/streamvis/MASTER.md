# StreamVis Design System v2.0

> **现代数据可视化界面设计系统**  
> 设计风格：Clean, Minimal, Professional  
> 参考：ChatGPT, Claude, Notion, Linear

---

## 设计原则

1. **简洁至上** - 去除多余装饰，聚焦内容
2. **清晰层次** - 通过阴影、间距建立视觉层次
3. **流畅动效** - 150-350ms 的平滑过渡
4. **温暖色彩** - 避免纯黑纯白，使用温暖色调

---

## 色彩系统

### 主色调 (Primary)
```css
--primary-50: #f0fdfa   /* 最浅 */
--primary-100: #ccfbf1
--primary-200: #99f6e4
--primary-300: #5eead4
--primary-400: #2dd4bf
--primary-500: #14b8a6  /* 主色 */
--primary-600: #0d9488  /* 按钮等 */
--primary-700: #0f766e
--primary-800: #115e59
--primary-900: #134e4a  /* 最深 */
```

### 中性色 (Gray)
```css
--gray-0: #ffffff       /* 纯白 */
--gray-50: #fafaf9      /* 页面背景 */
--gray-100: #f5f5f4     /* 卡片背景 */
--gray-200: #e7e5e4     /* 边框 */
--gray-300: #d6d3d1     /* 分割线 */
--gray-400: #a8a29e     /* 禁用文字 */
--gray-500: #78716c     /* 辅助文字 */
--gray-600: #57534e     /* 次要文字 */
--gray-700: #44403c
--gray-800: #292524
--gray-900: #1c1917     /* 主文字 */
```

### 语义化颜色
```css
/* 背景 */
--bg-primary: #ffffff      /* 卡片、面板 */
--bg-secondary: #fafaf9    /* 页面背景 */
--bg-tertiary: #f5f5f4     /* 悬停背景 */

/* 文字 */
--text-primary: #1c1917      /* 标题、正文 */
--text-secondary: #57534e    /* 次要文字 */
--text-tertiary: #78716c     /* 辅助说明 */
--text-quaternary: #a8a29e   /* 占位符 */

/* 边框 */
--border-subtle: rgba(0,0,0,0.05)  /* 细边框 */
--border-light: #e7e5e4           /* 输入框 */
--border-default: #d6d3d1         /* 按钮边框 */
```

---

## 布局系统

### 整体布局
```
┌─────────────────────────────────────────────┐
│  Sidebar (260px)   │  Main Content          │
│                    │  ┌─────────────────┐   │
│  Logo              │  │ Header          │   │
│                    │  ├─────────────────┤   │
│  Navigation        │  │                 │   │
│  - New Chat        │  │ Viz Section     │   │
│  - Upload          │  │ (Graph/Chart)   │   │
│  - Voice           │  │                 │   │
│                    │  ├─────────────────┤   │
│  Footer            │  │ Chat Section    │   │
│  - Status          │  │ (Messages)      │   │
│                    │  │ [Input Area]    │   │
└────────────────────┘  └─────────────────┘   │
```

### 响应式断点
| 断点 | 宽度 | 布局变化 |
|------|------|----------|
| Desktop | >1024px | 双栏布局，侧边栏固定 |
| Tablet | 768-1024px | 侧边栏可收起，单栏 |
| Mobile | <768px | 侧边栏滑出，堆叠布局 |

---

## 组件规范

### 按钮 (Button)

**Primary Button**
```css
.btn-primary {
  background: #0d9488;
  color: white;
  padding: 10px 20px;
  border-radius: 10px;
  font-weight: 500;
  font-size: 14px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
  transition: all 150ms ease;
}
.btn-primary:hover {
  background: #0f766e;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(13,148,136,0.25);
}
```

**Secondary Button**
```css
.btn-secondary {
  background: #f5f5f4;
  color: #57534e;
  border: 1px solid #e7e5e4;
  padding: 10px 20px;
  border-radius: 10px;
}
.btn-secondary:hover {
  background: #e7e5e4;
  color: #1c1917;
}
```

### 消息气泡 (Message Bubble)

**用户消息 - 参考 Claude 设计**
```css
.message-user {
  background: #f0efea;        /* 温暖灰色 */
  color: #1c1917;
  border-radius: 16px;
  border-bottom-right-radius: 6px;  /* 不对称圆角 */
  padding: 12px 16px;
}
```

**AI 消息**
```css
.message-assistant {
  background: #f5f5f4;
  color: #1c1917;
  border-radius: 16px;
  border-bottom-left-radius: 6px;
  padding: 12px 16px;
}
```

**系统消息**
```css
.message-system {
  background: rgba(14, 165, 233, 0.08);
  color: #0284c7;
  border-radius: 999px;
  padding: 6px 12px;
  font-size: 12px;
}
```

### 输入框 (Input)
```css
.input {
  height: 44px;
  padding: 0 16px;
  background: #fafaf9;
  border: 1px solid #e7e5e4;
  border-radius: 12px;
  font-size: 14px;
  transition: all 150ms ease;
}
.input:hover {
  border-color: #d6d3d1;
}
.input:focus {
  background: #ffffff;
  border-color: #0d9488;
  box-shadow: 0 0 0 3px rgba(13,148,136,0.08);
}
```

### 卡片/面板 (Card/Panel)
```css
.panel {
  background: #ffffff;
  border-radius: 16px;
  border: 1px solid rgba(0,0,0,0.05);
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
```

---

## 阴影系统

| 名称 | 值 | 用途 |
|------|-----|------|
| xs | `0 1px 2px rgba(0,0,0,0.03)` | 最小提升 |
| sm | `0 1px 3px rgba(0,0,0,0.04)` | 按钮、标签 |
| md | `0 4px 6px -1px rgba(0,0,0,0.04)` | 卡片悬停 |
| lg | `0 10px 15px -3px rgba(0,0,0,0.04)` | 下拉菜单 |
| xl | `0 20px 25px -5px rgba(0,0,0,0.05)` | 模态框 |
| accent | `0 4px 14px rgba(13,148,136,0.25)` | 主按钮悬停 |

---

## 圆角系统

| Token | 值 | 用途 |
|-------|-----|------|
| sm | 6px | 小按钮、标签 |
| md | 8px | 输入框 |
| lg | 12px | 卡片 |
| xl | 16px | 大卡片、消息气泡 |
| 2xl | 20px | 输入区域 |
| full | 9999px | 圆形、胶囊形 |

---

## 动画系统

### 时长
| 名称 | 值 | 用途 |
|------|-----|------|
| fast | 100ms | 颜色变化 |
| normal | 150ms | 悬浮效果 |
| slow | 250ms | 元素显示 |
| slower | 350ms | 消息入场 |

### 缓动函数
| 名称 | 值 | 用途 |
|------|-----|------|
| ease-out | `cubic-bezier(0,0,0.2,1)` | 大多数动画 |
| spring | `cubic-bezier(0.34,1.56,0.64,1)` | 消息入场 |

### 关键动画
```css
/* 消息入场 */
@keyframes messageIn {
  from {
    opacity: 0;
    transform: translateY(12px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 加载旋转 */
@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 脉冲 */
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
```

---

## 图表设计

### 配色
```css
/* 节点 */
--node-fill: #0d9488;
--node-stroke: #ffffff;
--node-shadow: rgba(0,0,0,0.15);

/* 连线 */
--link-stroke: #d6d3d1;

/* 文字 */
--text-label: #57534e;
```

### 折线图
```css
/* 线条 */
--line-stroke: #0d9488;
--line-width: 3px;

/* 区域填充渐变 */
--area-gradient: linear-gradient(180deg, rgba(13,148,136,0.3), rgba(13,148,136,0.02));

/* 数据点 */
--dot-fill: #0d9488;
--dot-stroke: #ffffff;
--dot-stroke-width: 2.5px;
```

---

## 最佳实践

### Do ✅
- 使用不对称圆角（消息气泡）
- 保持充足的留白（最小 16px）
- 使用温暖的中性色而非纯黑纯白
- 添加 150ms 的过渡动画
- 悬浮时轻微上移（-1px）
- 使用阴影而非边框来区分层次

### Don't ❌
- 避免使用 Emoji 作为图标
- 避免纯黑（#000）和纯白（#fff）
- 避免剧烈的动画和颜色变化
- 避免小于 12px 的文字
- 避免缺失焦点状态

---

## 更新日志

### v2.0 (2026-01-30)
- 全新现代化设计
- 参考 ChatGPT/Claude 的消息设计
- 新增侧边栏导航
- 优化色彩系统
- 改进动效设计
