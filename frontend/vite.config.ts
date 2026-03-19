import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) {
            return
          }

          if (id.includes('element-plus/es/components/')) {
            const componentMatch = id.match(/element-plus\/es\/components\/([^/]+)/)
            const componentName = componentMatch?.[1]

            if (componentName === 'container' || componentName === 'avatar' || componentName === 'icon') {
              return 'ep-layout'
            }

            if (componentName === 'button' || componentName === 'input' || componentName === 'scrollbar') {
              return 'ep-input'
            }

            if (componentName === 'dropdown') {
              return 'ep-overlay'
            }

            if (componentName === 'message' || componentName === 'message-box') {
              return 'ep-feedback'
            }

            if (componentName) {
              return `ep-${componentName}`
            }
          }

          if (id.includes('markdown-it')) {
            return 'markdown'
          }

          return 'vendor'
        }
      }
    }
  },
  test: {
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    exclude: ['e2e/**', 'node_modules/**', 'dist/**']
  },
  server: {
    port: 4173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        ws: true,
      }
    }
  }
})
