# AI Trading Platform Frontend

This is the frontend application for the AI Trading Platform, built with Next.js, React, and TypeScript.

## Features

- **Modern UI/UX**: Built with Tailwind CSS and Headless UI components
- **Real-time Data**: WebSocket integration for live market data
- **State Management**: Zustand for efficient state management
- **Type Safety**: Full TypeScript implementation
- **Responsive Design**: Mobile-first responsive design
- **Authentication**: JWT-based authentication with secure token management
- **Charts & Analytics**: Interactive charts and data visualizations

## Tech Stack

- **Framework**: Next.js 14
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **State Management**: Zustand
- **HTTP Client**: Axios
- **Data Fetching**: SWR
- **UI Components**: Headless UI, Heroicons
- **Charts**: Recharts
- **Forms**: React Hook Form with Yup validation
- **Animations**: Framer Motion
- **Notifications**: React Hot Toast

## Getting Started

### Prerequisites

- Node.js 18+ 
- npm or yarn
- Backend services running (API, Data Service, ML Service)

### Installation

1. Install dependencies:
```bash
npm install
```

2. Set up environment variables:
```bash
cp .env.local.example .env.local
```

3. Configure your environment variables in `.env.local`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_DATA_SERVICE_URL=http://localhost:8002
NEXT_PUBLIC_ML_SERVICE_URL=http://localhost:8003
NEXT_PUBLIC_WS_URL=ws://localhost:8002
```

4. Run the development server:
```bash
npm run dev
```

5. Open [http://localhost:3000](http://localhost:3000) in your browser.

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run start` - Start production server
- `npm run lint` - Run ESLint
- `npm run type-check` - Run TypeScript type checking
- `npm test` - Run tests
- `npm run test:watch` - Run tests in watch mode
- `npm run test:coverage` - Run tests with coverage

## Project Structure

```
frontend/
├── public/                 # Static files
├── src/
│   ├── components/        # Reusable UI components
│   │   ├── ui/           # Base UI components
│   │   └── layout/       # Layout components
│   ├── pages/            # Next.js pages
│   ├── store/            # Zustand stores
│   ├── types/            # TypeScript type definitions
│   ├── utils/            # Utility functions
│   ├── hooks/            # Custom React hooks
│   ├── api/              # API client functions
│   └── styles/           # Global styles
├── next.config.js        # Next.js configuration
├── tailwind.config.js    # Tailwind CSS configuration
└── tsconfig.json         # TypeScript configuration
```

## Key Components

### Layout Components
- `Layout` - Main application layout
- `Header` - Navigation header with user menu
- `Sidebar` - Navigation sidebar with menu items

### UI Components
- `Button` - Customizable button component
- `Card` - Card component with header/body/footer
- `Input` - Form input components
- `Modal` - Modal dialog component

### Store Management
- `authStore` - Authentication state management
- `marketStore` - Market data state management
- `portfolioStore` - Portfolio data state management

## Routing

- `/` - Landing page
- `/dashboard` - Main dashboard
- `/portfolio` - Portfolio overview
- `/trading` - Trading interface
- `/market-data` - Market data explorer
- `/ai-insights` - AI predictions and insights
- `/news` - Financial news
- `/watchlists` - Symbol watchlists
- `/settings` - User settings
- `/auth/login` - User login
- `/auth/register` - User registration

## Development Guidelines

### Code Style
- Use TypeScript for all components
- Follow ESLint configuration
- Use Tailwind CSS for styling
- Implement responsive design
- Write descriptive component props interfaces

### State Management
- Use Zustand stores for global state
- Keep component state local when possible
- Implement proper error handling
- Use loading states for async operations

### API Integration
- Use SWR for data fetching
- Implement proper error handling
- Use TypeScript interfaces for API responses
- Handle loading and error states

## Building for Production

1. Build the application:
```bash
npm run build
```

2. Start the production server:
```bash
npm run start
```

## Environment Variables

Required environment variables:

- `NEXT_PUBLIC_API_URL` - Backend API URL
- `NEXT_PUBLIC_DATA_SERVICE_URL` - Data service URL
- `NEXT_PUBLIC_ML_SERVICE_URL` - ML service URL
- `NEXT_PUBLIC_WS_URL` - WebSocket URL
- `NEXT_PUBLIC_APP_NAME` - Application name
- `NEXT_PUBLIC_ENV` - Environment (development/production)

## Contributing

1. Follow the existing code style
2. Write TypeScript interfaces for new features
3. Implement proper error handling
4. Add responsive design considerations
5. Test components thoroughly

## License

This project is part of the AI Trading Platform and is proprietary software.