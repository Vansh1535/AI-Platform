# AI Platform Frontend

A futuristic, production-ready frontend for the Enterprise RAG Platform built with Next.js 14, featuring a stunning neon-themed UI with 3D animations and real-time data visualization.

## 🎨 Features

- **Modern Stack**: Next.js 14 (App Router), TypeScript, Tailwind CSS
- **Futuristic Design**: Neon gradients, comic-style panels, glassmorphism
- **3D Animations**: Three.js integration for immersive visuals
- **Responsive**: Mobile-first design, works on all devices
- **Real-time**: TanStack Query for data fetching and caching
- **Type-Safe**: Full TypeScript coverage with backend API types

## 🚀 Quick Start

### Prerequisites

- Node.js 18+ 
- npm or yarn
- Backend API running on `http://localhost:8000` (or configure `.env.local`)

### Installation

```bash
# Navigate to frontend directory
cd Frontend_AIPROJ

# Install dependencies
npm install

# Start development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## 📁 Project Structure

```
Frontend_AIPROJ/
├── app/
│   ├── (dashboard)/          # Dashboard routes with layout
│   │   ├── documents/        # Document management (TODO)
│   │   ├── rag/             # Search & Q&A (TODO)
│   │   ├── analytics/       # CSV analytics (TODO)
│   │   ├── agent/           # AI agent (TODO)
│   │   ├── ml/              # ML predictions (TODO)
│   │   ├── summarize/       # Summarization (TODO)
│   │   ├── export/          # Export reports (TODO)
│   │   └── health/          # System health (TODO)
│   ├── layout.tsx           # Root layout
│   ├── page.tsx             # Landing page
│   └── globals.css          # Global styles
├── components/
│   ├── ui/                  # Radix UI components
│   ├── sidebar.tsx          # Navigation sidebar
│   ├── navbar.tsx           # Top navbar
│   └── providers.tsx        # React Query provider
├── lib/
│   ├── api/
│   │   ├── client.ts        # Axios instance
│   │   └── endpoints.ts     # API functions
│   ├── store/               # Zustand stores
│   ├── types/               # TypeScript types
│   └── utils.ts             # Utility functions
└── public/                  # Static assets
```

## 🎨 Design System

### Colors
- **Neon Cyan**: `#00F0FF` - Primary actions
- **Electric Magenta**: `#FF00FF` - Alerts, highlights
- **Deep Purple**: `#8B00FF` - Secondary elements
- **Acid Green**: `#39FF14` - Success states
- **Hot Pink**: `#FF006E` - Errors

### Components
- **Comic Panels**: Thick borders with neon glow
- **Glassmorphism**: Backdrop blur with transparency
- **Animations**: Framer Motion for smooth transitions

## 🔧 Configuration

### Environment Variables

Create `.env.local`:

```bash
# Backend API URL
NEXT_PUBLIC_API_URL=http://localhost:8000

# Mock data mode (true for demo without backend)
NEXT_PUBLIC_USE_MOCK_DATA=false
```

### API Integration

The frontend is 100% compatible with the FastAPI backend. All endpoints are typed and ready:

- `POST /rag/ingest-file` - Upload documents
- `GET /rag/docs/list` - List documents
- `POST /rag/query` - Semantic search
- `POST /rag/answer` - Q&A with citations
- `GET /rag/analytics/csv/{id}` - CSV insights
- `POST /agent/run` - AI agent execution
- `POST /ml/predict` - ML predictions
- `POST /export/report` - Generate reports
- `GET /health` - System health

## 📱 Pages

### ✅ Completed
- **Landing Page** (`/`) - Hero, features, stats
- **Dashboard Layout** - Sidebar navigation, responsive
- **Core UI Components** - Button, Card, Input, Dialog, Toast, etc.

### 🚧 TODO (Build these next)
1. **Documents Page** (`/documents`) - Upload, list, preview
2. **RAG Page** (`/rag`) - Search and Q&A interface
3. **Analytics Page** (`/analytics`) - CSV insights dashboard
4. **Agent Page** (`/agent`) - AI orchestrator
5. **ML Page** (`/ml`) - Prediction interface
6. **Summarize Page** (`/summarize`) - Document summaries
7. **Export Page** (`/export`) - Report generation
8. **Health Page** (`/health`) - System monitoring

## 🛠️ Development

```bash
# Development mode with hot reload
npm run dev

# Build for production
npm run build

# Start production server
npm start

# Run linting
npm run lint
```

## 📦 Dependencies

### Core
- `next` - React framework
- `react` - UI library
- `typescript` - Type safety

### UI
- `@radix-ui/*` - Accessible components
- `tailwindcss` - Styling
- `framer-motion` - Animations
- `lucide-react` - Icons
- `recharts` - Data visualization
- `@react-three/fiber` - 3D graphics

### Data
- `@tanstack/react-query` - Server state
- `axios` - HTTP client
- `zustand` - Client state
- `react-hook-form` - Form handling

## 🎯 Next Steps

1. **Install dependencies**: `npm install`
2. **Start dev server**: `npm run dev`
3. **Start backend**: Ensure FastAPI is running on port 8000
4. **Build remaining pages**: Follow TODO list above
5. **Test integration**: Upload documents, run queries
6. **Deploy**: Build and deploy to Vercel/Netlify

## 🔗 Backend Integration

This frontend connects to the FastAPI backend. Make sure:
1. Backend is running on `http://localhost:8000`
2. PostgreSQL database is initialized
3. ChromaDB is accessible
4. All environment variables are set in backend

## 📝 Notes

- The landing page is fully functional
- Sidebar navigation is responsive with mobile support
- All API endpoints are typed and ready to use
- Toast notifications are globally available
- Dark mode is the primary theme (neon aesthetic)

## 🤝 Contributing

This is a production-ready base. To extend:
1. Create page components in `app/(dashboard)/[page]/page.tsx`
2. Add API calls using functions from `lib/api/endpoints.ts`
3. Use TanStack Query hooks for data fetching
4. Follow the neon design system for consistency

## 📄 License

Enterprise RAG Platform - Proprietary

---

**Status**: Base structure complete ✅ | Pages in progress 🚧

Ready to build the remaining pages! 🚀
