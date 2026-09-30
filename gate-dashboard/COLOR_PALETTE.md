# Neobrutalism Design System

Single source of truth for the Gate Dashboard's visual language.

The UI was converted from the old teal/slate theme to **neobrutalism**: thick ink
outlines, hard offset shadows with zero blur, flat saturated fills, and heavy
geometric type. This document describes the system as it is actually
implemented.

## The four rules

Every component in the app obeys these. If you are adding a surface, these are
the checklist.

1. **Flat fill, never a gradient.** Solid colour only.
2. **Outlined.** `border-2 border-ink` on every surface.
3. **Raised surfaces drop a hard shadow.** `shadow-nb` — offset, `0` blur.
4. **Text on an accent fill is always ink.** Never white on a colour.

### What the style forbids

These were deliberately removed and should not come back:

| Forbidden | Why |
| --- | --- |
| Gradients (`bg-gradient-to-*`, `linear-gradient`) | Soft shading contradicts the flat-ink look |
| Translucent panels | Same reason |
| `backdrop-blur-*` | Glassmorphism, not neobrutalism |
| `dark:` variants | There is no dark-mode toggle. `.dark` exists in `index.css` but is never applied |
| Soft shadows (`shadow-sm`, `shadow-lg`, `drop-shadow`) | Only the hard `--nb-shadow-*` steps are used |
| Pill/rounded-full buttons and badges | Corners are square or near-square |
| Thin hairline borders | 2px ink is the house weight |

A handful of translucency utilities remain, but only where a soft value is
load-bearing rather than decorative:

- `bg-ink/70` — modal scrim (the overlay must dim what is behind it)
- `border-ink/20` — skeleton placeholder
- `text-ink/70` — secondary text on already-saturated card header bars
- `border-background/20` — sidebar dividers, which sit on the ink block
- `hsl(var(--ink) / 0.14)` inside `.nb-stripes`

## Canvas and ink

One variable, `--ink`, drives **borders, shadows and body text**. This is the
single most important rule in the system: it is what makes everything read as
one family.

| Token | Value | Hex | Use |
| --- | --- | --- | --- |
| `--ink` | `24 14% 8%` | `#141414` | All borders, all shadows, body text |
| `--background` | `42 33% 95%` | `#F7F2E7` | Page canvas (warm paper) |
| `--card` | `0 0% 100%` | `#FFFFFF` | Card surface |
| `--muted` | `42 22% 89%` | `#EDE7DA` | Secondary panels, table head fill |
| `--muted-foreground` | `35 12% 32%` | `#514B40` | Body copy on paper |
| `--radius` | — | `0.5rem` | Deliberately small. Corners stay crisp |

The canvas is warm paper, not white, so that pure-white cards read as a raised
layer against it.

## Accent set

Eight flat accents, defined once in `tailwind.config.js` as `nb.*` and mirrored
as fill utilities in `index.css`. There is no tint/shade ladder — you get the
one value.

| Accent | Hex | Tailwind fill | Utility class |
| --- | --- | --- | --- |
| Yellow | `#FFD83D` | `bg-nb-yellow` | `.nb-yellow` |
| Blue | `#4A7DFF` | `bg-nb-blue` | `.nb-blue` |
| Green | `#3DD68C` | `bg-nb-green` | `.nb-green` |
| Red | `#FF5A5F` | `bg-nb-red` | `.nb-red` |
| Orange | `#FF8A3D` | `bg-nb-orange` | `.nb-orange` |
| Purple | `#C08BFF` | `bg-nb-purple` | `.nb-purple` |
| Cyan | `#3DD6E8` | `bg-nb-cyan` | `.nb-cyan` |
| Pink | `#FF6FB5` | `bg-nb-pink` | `.nb-pink` |

All eight take ink text, comfortably past WCAG AAA for large text and above AA
for body copy. Yellow is the brand primary.

### Semantic roles

Meaning is centralised in `src/styles/tokens.ts` (`accents`) so a status, its
icon tile and its badge can never disagree.

| Role | Accent | Meaning |
| --- | --- | --- |
| `primary` | yellow | Brand, primary action |
| `success` | green | Allowed, active, OPEN |
| `danger` | red | Denied, revoked, destructive action |
| `warning` | orange | Caution, deactivated |
| `info` | cyan | Informational |
| `entry` | blue | ENTRY gate |
| `exit` | green | EXIT gate |
| `rfid` | purple | RFID access method |
| `qr` | blue | QR access method |
| `anpr` | cyan | ANPR access method |
| `manual` | orange | Manual access method |
| `ticket` | pink | Ticket-centric surfaces |

Ticket-type accents live in `getTicketAccent()`: `SINGLE_ENTRY` → cyan,
`MULTI_DAY` → purple, `VIP` → yellow, `STAFF` → green.

## Token exports (`src/styles/tokens.ts`)

Prefer these over hand-writing class strings.

| Export | Shape | Use |
| --- | --- | --- |
| `nb[accent]` | `bg-nb-* border-ink` | A filled, outlined box |
| `nbFill[accent]` | `bg-nb-*` | A fill inside an already-outlined box |
| `tile[accent]` | `bg-nb-* border-ink` | Square icon tile |
| `accents` | semantic → accent | Look up meaning, never colour |
| `badge.*` | ready badge classes | Entry/exit/success/danger/warning/info/neutral/primary |
| `getMethodLabel(m)` | Indonesian string | Display text for an access method |
| `getTicketLabel(t)` | Indonesian string | Display text for a ticket type |
| `getMethodAccent`, `getTicketAccent` | `Accent` | Colour lookup |
| `getMethodBadge`, `getTicketBadge` | class string | Ready-made badge |

**Display labels are centralised deliberately.** A ticket type was once rendered
via `type.replace('_', ' ')` in the table while the filter dropdown above it said
"Sekali Masuk" — the same value spelled two ways on one screen. Use
`getTicketLabel()` / `getMethodLabel()` in both the cell and its filter.

Indonesian labels: `RFID` → Kartu RFID, `ANPR` → ANPR / Plat, `QR` → Scan QR,
`MANUAL` → Manual; `SINGLE_ENTRY` → Sekali Masuk, `MULTI_DAY` → Multi Hari,
`VIP` → VIP, `STAFF` → Staf.

## Components

### Buttons (`components/ui/button.tsx`)

`border-2 border-ink font-bold uppercase tracking-wide` + `nb-press`.
Text is always ink.

| Variant | Fill | Use |
| --- | --- | --- |
| `default` | `bg-primary` (yellow) | Primary action |
| `destructive` | `bg-destructive` (red) | Delete, revoke, cancel-with-consequence |
| `secondary` | `bg-secondary` (blue) | Secondary action |
| `outline` | `bg-card` | Neutral action |
| `ghost` | transparent | Low-emphasis |
| `link` | transparent, no border | Inline text action |

Sizes: `sm` `h-9`, `default` `h-11`, `lg` `h-12`, `icon` `h-11 w-11`.
`h-11` is the default touch/click target and the width used by dialog footers,
table controls and pagination — keep new interactive controls on that grid.

### Cards

`Card` → `flex flex-col overflow-hidden`; `CardContent` → `flex-1`.

That pair is what makes grids symmetric: `CardContent` absorbs the slack so a
`mt-auto` control pins to the card's bottom edge and every card in a row ends at
the same height. Card headers are **full-width flat colour bars**, not tinted rows.

Neobrutalism leans on hard geometry, so prefer `auto-rows-fr` on a grid column
over magic `min-h` values when you need equal-height rows.

### Badges

```
bg-nb-<accent> text-ink border-ink
```

Solid fill with a 2px ink border. No tints, no `text-<colour>-700` on a pale
background — that was the old theme.

### Dialogs (`components/ui/dialog.tsx`)

- `Dialog` owns the overlay **and** the card. It is the single place a scrim
  exists, which is what stops nested dialogs from double-dimming.
- `DialogContent` is a plain layout div — no overlay, no card chrome.
- `DialogHeader` is canonical: `icon` / `tone` / `title` / `description` / `right`.
  The icon tile is a fixed `h-11 w-11` and the title block is `flex-1`, so a long
  description can never shift the tile out of vertical alignment with the title.
  The header is full-bleed and sticky.
- `DialogFooter` is the single owner of footer chrome:
  `mt-5 flex flex-col-reverse gap-3 border-t-2 border-ink pt-4 sm:flex-row sm:justify-end sm:[&>button]:flex-1`
- `size` accepts `sm | md | lg`; Escape closes.

**On the footer:** the `sm:` prefix on `[&>button]:flex-1` is deliberate. Scoped
to `sm` and up, mobile keeps a stacked column; unscoped, `flex-1` would stretch
buttons *vertically* in that column. Equal-width pairing uses `[&>button]`, not
`[&>*]`, so a non-button child (hint text) is left alone. Because the component
runs through `cn`/`twMerge`, a caller can override the layout outright — e.g.
`grid grid-cols-2` for a 2×2 action grid, which makes the `sm:` rules inert.

Use `<DialogFooter>`; do not re-declare the `border-t-2 … pt-4` rule inline.
Three copies of that markup were consolidated during the redesign.

### Tabs (`components/ui/tabs.tsx`)

Built on React context, **controlled or uncontrolled**. Only the active panel is
mounted, so inactive panels cannot leak stale state. Settings uses the controlled
form (`value` + `onValueChange`).

### Tables (`components/ui/table.tsx`)

`TableHead` is `h-11 whitespace-nowrap` so every header stays on one line and
the whole row shares a single baseline. The wrapper is `overflow-auto`, so a
narrow viewport scrolls the table rather than wrapping headers.

### Shared primitives

- `StatCard` + `Meter` — `components/ui/stat-card.tsx`
- `Pagination` — `components/ui/pagination.tsx`, `variant?: 'card' | 'strip'`,
  all controls `h-11`

## Layout patterns

**Page rhythm.** Top-level page containers use `space-y-6`. Dashboard is no
exception.

**Table action buttons are icon-only** (QR, trash) with an Indonesian
`aria-label` and `title` — that pair is the only accessible name. Playwright and
any click-matching harness must match on it.

**Data-driven tones are intentional.** RFID row actions are green for activate
and orange for deactivate; a checkered mix of the two is semantic, not a bug.
Likewise an admin user row with no action buttons.

## Typography

`body` is `font-weight: 600`; headings are `800` with `letter-spacing: -0.03em`
and `line-height: 1.1`; buttons are `700` and `uppercase`. The two utilities:

- `.nb-label` — `11px / 800 / 0.08em / uppercase`, for small caps labels
- `.nb-pulse` — hard `scale(1) → scale(1.12)` attention cue, no easing softness

Page titles, table headers, buttons, badges, toasts and `aria-label`s are all in
**Indonesian**. Console logs are left in English on purpose — they are for
developers, not operators. `index.html` carries `lang="id"`.

## CSS primitives (`src/index.css`)

Prefer these over ad-hoc utilities.

| Class | Purpose |
| --- | --- |
| `.nb-shadow-sm` / `-nb` / `-nb-lg` | `2px` / `4px` / `6px` offset, `0` blur |
| `.nb-shadow-none` | Flatten (modals, pressed state) |
| `.nb-press` | Lift on hover, **slam down onto the shadow on active** |
| `.nb-card` / `.nb-card-hover` | Outlined + raised card, lifts on hover |
| `.nb-label` | Small caps label |
| `.nb-stripes` | Diagonal caution stripes |
| `.nb-divider` | Thick rule |
| `.nb-*` / `.nb-text-*` | Flat accent fills and text colours |

Native control chrome is normalised in `index.css`: number-input spinners and
the textarea resize grip are removed, and the date-picker glyph is grayscaled
and contrast-boosted so it matches the ink border. The calendar still opens on
click.

## Checklist for a new component

- [ ] `border-2 border-ink` on the surface
- [ ] `shadow-nb` if it is raised; `.nb-press` if it is clickable
- [ ] Flat fill — no gradient, no translucency, no `backdrop-blur`
- [ ] Text on a colour is `text-ink`
- [ ] No `dark:` variant (there is no theme toggle)
- [ ] Square or near-square corners
- [ ] Accent chosen via `accents` / a `get*Accent()` helper, not hand-picked
- [ ] Display text via `get*Label()`, so it matches its own filter
- [ ] Indonesian copy for anything a user reads or a screen reader announces
- [ ] Interactive controls land on the `h-11` grid
- [ ] Inside a card, content uses `flex-1` / `mt-auto` so rows stay symmetric
