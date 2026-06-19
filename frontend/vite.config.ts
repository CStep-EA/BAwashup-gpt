import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { VitePWA } from 'vite-plugin-pwa'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.svg', 'apple-touch-icon.png', 'bower-ag-logo.jpg', 'barn-icon-red.jpg'],
      manifest: {
        name: 'Bower Ag CowCare Tool',
        short_name: 'CowCare',
        description: 'Expert system for dairy cow care consulting',
        theme_color: '#9b3426',
        background_color: '#ffffff',
        display: 'standalone',
        scope: '/',
        start_url: '/',
        icons: [
          {
            src: 'pwa-192x192.png',
            sizes: '192x192',
            type: 'image/png',
          },
          {
            src: 'pwa-512x512.png',
            sizes: '512x512',
            type: 'image/png',
          },
          {
            src: 'pwa-512x512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'any maskable',
          },
        ],
      },
      workbox: {
        // Cache API calls for offline resilience
        runtimeCaching: [
          {
            // Cache product catalog API responses
            urlPattern: /\/api\/governance\/(product|pricing)/,
            handler: 'StaleWhileRevalidate',
            options: {
              cacheName: 'governance-api-cache',
              expiration: {
                maxEntries: 100,
                maxAgeSeconds: 60 * 60, // 1 hour
              },
            },
          },
          {
            // Cache RAG search results
            urlPattern: /\/api\/rag\/search/,
            handler: 'NetworkFirst',
            options: {
              cacheName: 'rag-search-cache',
              expiration: {
                maxEntries: 50,
                maxAgeSeconds: 30 * 60, // 30 minutes
              },
            },
          },
          {
            // Cache Google Fonts
            urlPattern: /^https:\/\/fonts\.googleapis\.com\/.*/i,
            handler: 'CacheFirst',
            options: {
              cacheName: 'google-fonts-cache',
              expiration: {
                maxEntries: 10,
                maxAgeSeconds: 60 * 60 * 24 * 365, // 1 year
              },
            },
          },
        ],
        // Navigate fallback for SPA routing
        navigateFallback: '/index.html',
        navigateFallbackDenylist: [/^\/api\//],
      },
    }),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    host: true,
    allowedHosts: true,
  },
})
