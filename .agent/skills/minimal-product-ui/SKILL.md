---
name: minimal-product-ui
description: Design principles and rules for clean, minimal, human-crafted product UI without AI clichés
---

# Minimal Product UI Skill

This skill enforces high-craft, minimal, utilitarian, and calm UI/UX design suitable for a dependable student study tool.

## Core Rules

1. **Color Palette**
   - Base: Pure white `#FFFFFF` and neutral grays (Slate/Zinc `slate-50` to `slate-900`).
   - Accent: Exactly ONE calm muted accent color (e.g. Muted Indigo `#4F46E5` / Tailwind `indigo-600` or Muted Teal `teal-700`).
   - Semantic Status:
     - Success: Muted emerald (`emerald-600`)
     - Warning: Muted amber (`amber-600`)
     - Error: Crimson/Rose (`rose-600`)
   - **STRICTLY FORBIDDEN**: Gradients, bright purple-to-cyan gradients, neon glow, neon borders, glassmorphism, background blobs, stock marketing illustrations, decorative emojis in headings.

2. **Typography**
   - Font family: Clean system sans or Inter (`font-sans`). Exactly one font family across the app.
   - Scale:
     - Heading 1: `text-2xl font-semibold tracking-tight text-slate-900`
     - Heading 2: `text-lg font-medium text-slate-900`
     - Body: `text-sm text-slate-600 leading-relaxed`
     - Micro/Meta: `text-xs text-slate-500 font-mono` or `font-normal`
   - Alignment: Left-aligned content. No centered multi-line body paragraphs.

3. **Layout & Spacing**
   - 4px / 8px grid (`p-2`, `p-4`, `p-6`, `gap-3`, `gap-4`, `gap-6`).
   - Simple top bar: Left title/logo ("VTU Study Planner"), right navigation links ("Planner", "Library").
   - Max width: Single centered column `max-w-2xl` (~670-720px) for configuration steps; wider container `max-w-4xl` or `max-w-5xl` for the timetable.
   - Mobile: 100% width with `px-4`, full responsiveness down to 360px viewport.

4. **Component Patterns**
   - **Cards**: `border border-slate-200 bg-white rounded-lg p-5` (no heavy drop shadows, max `shadow-sm`).
   - **Buttons**:
     - Primary: Solid accent `bg-indigo-600 text-white font-medium hover:bg-indigo-700 rounded-md px-4 py-2 text-sm transition-colors focus:ring-2 focus:ring-indigo-500 focus:outline-none`.
     - Secondary: `border border-slate-300 text-slate-700 hover:bg-slate-50 rounded-md px-4 py-2 text-sm font-medium`.
   - **Segmented Controls**: Bordered container `inline-flex p-1 bg-slate-100 rounded-md gap-1`. Active item: `bg-white shadow-xs text-slate-900 font-medium`.
   - **Inputs / Combobox**: `border border-slate-300 rounded-md px-3 py-2 text-sm text-slate-900 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500`.
   - **Radio Cards**: Selectable cards with subtle radio circle, distinct 1px border highlight (`border-indigo-600 bg-indigo-50/20`).

5. **Copywriting Tone**
   - Pragmatic, honest, student-first.
   - No hyperbole ("Supercharge your prep!", "Magic AI timetable!").
   - Clear indicators of external sources and honest warnings.

## QA Review Checklist
- [ ] No gradient backgrounds or text gradients.
- [ ] No decorative emojis in headings.
- [ ] All inputs have explicit `<label>` tags.
- [ ] Mobile responsive without horizontal overflow at 375px.
- [ ] Loading spinners and skeleton states present for all async calls.
