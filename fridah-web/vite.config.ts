
import { defineConfig } from 'vitest/config'
import { loadEnv } from 'vite'
import { writeFileSync } from 'node:fs'
import { headersFile, nginxSnippet } from './build/securityHeaders.js'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig(({ mode }) => ({
  // GitHub Pages project URL: https://almasiTech1.github.io/FRIDAH/
  // Local development continues using the root path.
  base: mode === 'production' ? '/FRIDAH/' : '/',

  plugins: [vue(), {
    name: 'fridah-security-headers',
    apply: 'build' as const,
    closeBundle() {
      const api = loadEnv(mode, process.cwd(), 'VITE_').VITE_API_BASE_URL
      writeFileSync('dist/_headers', headersFile(api))
      writeFileSync('dist/security-headers.nginx.conf', nginxSnippet(api))
    },
  }],

  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },

  test: {
    environment: 'jsdom',
    globals: true,
    include: ['src/**/*.test.ts']
  },

  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'https://api.fridah.co.ke',
        changeOrigin: true,
      }
    }
  }
}))
