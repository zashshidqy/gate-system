/**
 * TEMPORARY screenshot-only vite config. Proxies the app at :5199 to the
 * isolated seeded backend on :8123 so the real Dashboard can be captured at
 * exact Tailwind breakpoints without touching the user's dev server or gate.db.
 *
 * Delete after screenshots are taken. Never commit.
 */
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    host: '127.0.0.1',
    port: 5199,
    strictPort: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8123',
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api/, ''),
      },
      '/ws': {
        target: 'ws://127.0.0.1:8123',
        ws: true,
        changeOrigin: true,
      },
    },
  },
})