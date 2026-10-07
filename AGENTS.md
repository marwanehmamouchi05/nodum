# Frontend tool usage

- Preserve working behavior and the existing React/TypeScript architecture. Tool setup is not permission to redesign, add dependencies, or initialize shadcn.
- Use Context7 for targeted library/API documentation: resolve the library, then query the specific concept. Avoid broad retrieval and repeated queries for unchanged context.
- Use shadcn MCP to search existing primitives before hand-building generic UI components; adapt to the current design system rather than installing automatically.
- Use Figma when structured design context materially helps; reuse the existing official connection.
- Load the `frontend-design` skill only for substantive UI design work. For Nodum, prioritize professional dashboard UX, readable typography, consistent spacing/tokens, responsive layouts, keyboard access, contrast, and honest loading/empty/error/simulation states.
- Preserve system/self-hosted fonts and privacy protections; do not add external font requests or analytics as visual polish.
- Use Playwright for visual QA after meaningful UI batches or when inspection is necessary, not after every CSS edit. Reinspect only affected screens and relevant mobile/tablet widths.
- Read targeted files first. Do not run overlapping browser tools or retrieve whole repositories/design files when a focused inspection is sufficient.
