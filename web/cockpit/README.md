# Agent Platform Cockpit

Next.js frontend for the Digital Twin Email Platform.

## Tech Stack

- **Framework:** Next.js 16 (App Router)
- **Language:** TypeScript
- **Styling:** Tailwind CSS
- **State Management:**
  - TanStack Query (server state)
  - Zustand (client state)
- **HTTP Client:** Axios
- **Icons:** Lucide React

---

## Getting Started

### 1. Install Dependencies

```bash
cd web/cockpit
npm install
```

### 2. Start Development Server

```bash
npm run dev
```

The app will be available at http://localhost:3000

### 3. Build for Production

```bash
npm run build
npm start
```

---

## Project Structure

```
src/
├── app/
│   ├── layout.tsx           # Root layout (Sidebar + Header)
│   ├── page.tsx             # Dashboard/Cockpit
│   ├── providers.tsx        # TanStack Query Provider
│   ├── globals.css          # Global styles
│   │
│   ├── email-agent/
│   │   ├── page.tsx         # Email-Agent Overview
│   │   └── runs/
│   │       └── [id]/
│   │           └── page.tsx # Run Detail
│   └── ...
│
├── components/
│   ├── layout/
│   │   ├── Sidebar.tsx      # Navigation sidebar
│   │   └── Header.tsx       # Top header
│   └── ui/                  # Reusable UI components
│
└── lib/
    ├── api/
    │   ├── client.ts        # Axios instance
    │   └── queries.ts       # TanStack Query hooks
    └── types/
        ├── email-agent.ts   # Email-Agent types
        └── dashboard.ts     # Dashboard types
```

---

## API Integration

The frontend connects to the FastAPI backend (port 8000) via proxy configured in `next.config.mjs`.

### API Client

```typescript
import { apiClient } from '@/lib/api/client';

// Example: Fetch data
const response = await apiClient.get('/email-agent/status');
```

### TanStack Query Hooks

```typescript
import { useEmailAgentStatus, useEmailAgentRuns } from '@/lib/api/queries';

function MyComponent() {
  const { data: status } = useEmailAgentStatus();
  const { data: runs } = useEmailAgentRuns({ limit: 10 });

  // ...
}
```

### Mutations

```typescript
import { useAcceptRun } from '@/lib/api/queries';

function MyComponent() {
  const acceptMutation = useAcceptRun();

  const handleAccept = (runId: string) => {
    acceptMutation.mutate({ runId, feedback: 'Looks good!' });
  };

  // ...
}
```

---

## Navigation Structure

| Route | Page | Status |
|-------|------|--------|
| `/` | Cockpit/Dashboard | ✅ Basic |
| `/email-agent` | Email-Agent Overview | ✅ Functional |
| `/email-agent/runs/[id]` | Run Detail | ⏳ Pending |
| `/agents` | Agents List | ⏳ Pending |
| `/inbox` | Inbox View | ⏳ Pending |
| `/chat` | Chat Interface | ⏳ Coming Soon |
| `/automations` | Automations/Playbooks | ⏳ Coming Soon |
| `/settings` | Settings | ⏳ Pending |

---

## Development Workflow

### Adding a New Page

1. Create page file: `src/app/my-page/page.tsx`
2. Add route to Sidebar: `src/components/layout/Sidebar.tsx`
3. Create types (if needed): `src/lib/types/my-page.ts`
4. Create API hooks (if needed): `src/lib/api/queries.ts`

### Adding a New API Endpoint

1. Add TypeScript types: `src/lib/types/*.ts`
2. Create query/mutation hook: `src/lib/api/queries.ts`
3. Use in component:
   ```tsx
   const { data } = useMyQuery();
   ```

---

## Environment Variables

No environment variables needed for development (API proxy is configured in `next.config.mjs`).

For production:

```env
# .env.local
NEXT_PUBLIC_API_URL=https://api.your-domain.com
```

---

## Styling Guidelines

### Tailwind Utilities

Common patterns used in the project:

```tsx
// Card
<div className="bg-white rounded-lg shadow p-6">

// Button (Primary)
<button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">

// Badge
<span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">

// Input
<input className="border border-gray-300 rounded-lg px-3 py-2" />
```

### Color Palette

- **Primary:** Blue (blue-600)
- **Success:** Green (green-600)
- **Warning:** Orange (orange-600)
- **Error:** Red (red-600)
- **Gray Scale:** gray-50 to gray-900

---

## Testing

```bash
# Run tests (when implemented)
npm test

# Type checking
npm run type-check
```

---

## Deployment

### Vercel (Recommended)

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel
```

### Docker

```dockerfile
FROM node:20-alpine

WORKDIR /app
COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

EXPOSE 3000
CMD ["npm", "start"]
```

---

## Next Steps

1. ✅ Next.js Setup + Layout
2. ⏳ Email-Agent Pages (Run Detail)
3. ⏳ Dashboard with real data
4. ⏳ Tasks/Decisions/Questions HITL Pages
5. ⏳ Journals Page
6. ⏳ Authentication (JWT)

---

## Troubleshooting

### Port already in use

```bash
# Kill process on port 3000
kill -9 $(lsof -t -i:3000)

# Or use different port
npm run dev -- -p 3001
```

### API Connection Issues

1. Check FastAPI is running on port 8000
2. Check proxy config in `next.config.mjs`
3. Check browser console for CORS errors

---

## Resources

- [Next.js Docs](https://nextjs.org/docs)
- [TanStack Query Docs](https://tanstack.com/query/latest)
- [Tailwind CSS Docs](https://tailwindcss.com/docs)
