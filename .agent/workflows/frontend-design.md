---
description: Design frontend premium avec aesthetics modernes et UX soignée
---

# Frontend Design Workflow

Quand tu utilises `/frontend-design`, applique ces standards :

## 1. Design System Obligatoire

### Couleurs (Dark Mode First)

```css
:root {
  /* Backgrounds */
  --bg-primary: #0a0a0f;
  --bg-secondary: #12121a;
  --bg-card: #1a1a24;
  --bg-hover: #252530;

  /* Accents */
  --accent-primary: #6366f1; /* Indigo */
  --accent-success: #22c55e; /* Green */
  --accent-warning: #f59e0b; /* Amber */
  --accent-danger: #ef4444; /* Red */

  /* Text */
  --text-primary: #f8fafc;
  --text-secondary: #94a3b8;
  --text-muted: #64748b;

  /* Borders */
  --border: rgba(255, 255, 255, 0.08);
  --border-hover: rgba(255, 255, 255, 0.15);
}
```

### Typography

```css
/* Google Fonts: Inter */
font-family: "Inter", -apple-system, BlinkMacSystemFont, sans-serif;

/* Hierarchy */
--font-xs: 0.75rem; /* 12px - labels */
--font-sm: 0.875rem; /* 14px - body small */
--font-base: 1rem; /* 16px - body */
--font-lg: 1.125rem; /* 18px - headings */
--font-xl: 1.25rem; /* 20px - titles */
--font-2xl: 1.5rem; /* 24px - page titles */
```

## 2. Components Standards

### Cards (Glassmorphism)

```css
.card {
  background: rgba(26, 26, 36, 0.8);
  backdrop-filter: blur(12px);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 24px;
  transition: all 0.2s ease;
}
.card:hover {
  border-color: var(--border-hover);
  transform: translateY(-2px);
}
```

### Buttons

```css
.btn-primary {
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: white;
  padding: 12px 24px;
  border-radius: 12px;
  font-weight: 600;
  transition: all 0.2s;
}
.btn-primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 8px 24px rgba(99, 102, 241, 0.3);
}
```

## 3. Animations (Subtiles mais Impactantes)

```css
/* Fade in on load */
@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Skeleton loading */
@keyframes shimmer {
  0% {
    background-position: -200% 0;
  }
  100% {
    background-position: 200% 0;
  }
}

/* Micro-interactions */
.interactive {
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.interactive:hover {
  transform: scale(1.02);
}
.interactive:active {
  transform: scale(0.98);
}
```

## 4. Layout Principles

### Spacing System (8px grid)

```
--space-1: 4px
--space-2: 8px
--space-3: 12px
--space-4: 16px
--space-6: 24px
--space-8: 32px
--space-12: 48px
--space-16: 64px
```

### Responsive Breakpoints

```css
/* Mobile first */
@media (min-width: 640px) {
  /* sm */
}
@media (min-width: 768px) {
  /* md */
}
@media (min-width: 1024px) {
  /* lg */
}
@media (min-width: 1280px) {
  /* xl */
}
```

## 5. Checklist Design Review

Avant de valider un design :

- [ ] Contraste accessible (WCAG AA minimum)
- [ ] États hover/focus/active définis
- [ ] Loading states ajoutés
- [ ] Empty states prévus
- [ ] Error states stylés
- [ ] Animations < 300ms
- [ ] Touch targets >= 44px (mobile)

## 6. Libraries Recommandées

### React/Next.js

- **Framer Motion** - Animations
- **Radix UI** - Composants accessibles
- **React Icons** - Icônes (Lucide ou Heroicons)
- **Recharts** - Graphiques

### CSS

- **Tailwind CSS** (si demandé par l'utilisateur)
- **CSS Modules** (par défaut)

## 7. Output attendu

Pour chaque composant créé :

1. **Preview mentale** de l'apparence
2. **États** : default, hover, active, disabled, loading
3. **Responsive** : mobile → desktop
4. **Accessibilité** : aria-labels, focus management
