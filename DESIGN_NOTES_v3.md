# OPC Radar v3 — "Paper Ledger" (warm paper + one cobalt ink)

Design read: daily curation feed for indie builders, calm editorial-technical, restrained motion.
Rejected & removed: violet aurora, lime accent, film grain, glass panels, tilted 3D hero, shimmer, marquee ticker.
Distinct from HowToLiveBetter (cold zinc #fafafa + green/blue, Inter) and UI Hub (cyan-pink): warm parchment, serif display, single cobalt.

## Skills read
- Leonxlnx/taste-skill (SKILL.md): anti-default rules — no AI-purple gradients, no glass everywhere, no Inter+slate; dials set to 6/3/5 (editorial feed).
- MengTo web-design/light-mode-paper-technical: warm paper surfaces, thin rules, corner brackets, one restrained accent, mono metadata, calm fade-up.
- MengTo web-design/beautiful-shadows: exact layered neutral shadows (sm/md) used verbatim as --sh-sm / --sh-md.

## Borrowed patterns (preview PNG → tokens)
| # | Library / preview | Pattern | Tokens |
|---|---|---|---|
| 1 | Radix Themes — previews/lib-www-radix-ui-com-themes.webp | Serif display headline + floating product card ("Your team") on right | Instrument Serif 400, clamp(40–68px), lh 1.02, ls -0.02em; card radius 14px, --sh-md |
| 2 | Cult UI — previews/www-cult-ui-com.webp | Display word in contrasting face (here italic serif in accent), mono footer rule | italic serif in #2448d8; Geist Mono 12px meta |
| 3 | Beautiful UI — previews/www-beautifului-dev.webp | Hatched diagonal gutters + bordered center column | repeating-linear-gradient(-45deg, 7px gap, 1px rgba(60,50,30,.07)); 1px #e2ddd1 column borders |
| 4 | Kibo UI — previews/www-kibo-ui-com.webp | Single cobalt brand ink | --acc #2448d8 light / #8aa2ff dark; soft #e6ebfb |
| 5 | Tremor — previews/lib-tremor-so.webp | Big tabular numbers + proportional bar KPI | Geist Mono 26px tabular-nums; 2px bar, width = n/max |
| 6 | ElevenLabs UI — previews/ui-elevenlabs-io.webp | "Introducing →" split pill; uneven card grid | pill radius 999, inner chip on accent-soft; 4-col bento, lead tile span 2 |
| 7 | Sonner / Vaul (Emil Kowalski) — lib-sonner-*, lib-vaul-* | Solid ink primary button + soft white secondary, press scale | btn h40 r10, :active scale(.98), hover -1px lift |
| 8 | shadcnblocks — www-shadcnblocks-com.webp | Bordered cell grid for channels | 1px hairline cells, arrow nudge 3px on hover |
Also viewed: originkit-dev.webp (rejected: neon particle look).

## Tokens
Light: bg #f4f1ea, paper #fbfaf6, sunk #efebe2, line #e2ddd1, fg #1c1b18 / #57534a / #8a8478, ok #2f7d4f.
Dark: bg #141310, paper #1c1b17, line #2e2b24, fg #f1ede3, acc #8aa2ff.
Type: Geist (UI), Instrument Serif (display/h2), Geist Mono (numbers/meta). Radius 14 / 10 / 8 / 999.
Motion: 0.7s fade-up cubic-bezier(.2,.7,.2,1); reduced-motion respected. Nothing loops.
