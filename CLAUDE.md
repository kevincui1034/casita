AGENTS.md

## web/ dashboard conventions

- Use shadcn/ui components whenever possible (`npx shadcn@latest add <component>`
  into `web/components/ui/`) instead of hand-rolling UI primitives. Compose and
  restyle them with Tailwind utility classes and the theme tokens in
  `web/app/globals.css`; do not reintroduce bespoke CSS component classes.
- Theme tokens live in `web/app/globals.css` (shadcn/Tailwind v4 layout,
  bright light theme, emerald primary). Change colors there, not inline.
- Note: `web/components/ui/scroll-area.tsx` carries a deliberate `[&>div]`
  override — Radix's viewport wrapper is `display: table`, which breaks
  flex-wrap/truncate inside; keep that override when regenerating the component.
- Scrolling: use NATIVE `overflow-y-auto` for long lists (the global thin
  scrollbar CSS keeps the minimal look) — Radix/shadcn ScrollArea positions
  its thumb from JS and visibly lags on long content. ScrollArea is fine for
  short regions like the detail drawer. Long lists also keep items memoized
  (see ListingCard) so hover state can't re-render the whole list mid-scroll.
