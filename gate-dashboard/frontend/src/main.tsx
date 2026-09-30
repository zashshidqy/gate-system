import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import App from './App'
import './index.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5000,
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
        <Toaster
          position="top-right"
          gutter={12}
          toastOptions={{
            duration: 4000,
            style: {
              border: '2px solid hsl(24 14% 8%)',
              borderRadius: '8px',
              boxShadow: '4px 4px 0 0 hsl(24 14% 8%)',
              background: 'hsl(0 0% 100%)',
              color: 'hsl(24 14% 8%)',
              fontWeight: 700,
              fontSize: '13px',
              padding: '12px 16px',
              maxWidth: '380px',
            },
            success: { style: { background: 'hsl(152 62% 56%)' } },
            error: { style: { background: 'hsl(358 100% 67%)' } },
            loading: { style: { background: 'hsl(48 100% 62%)' } },
          }}
        />
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
)