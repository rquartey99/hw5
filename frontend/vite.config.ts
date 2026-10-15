import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Dev server on 5173 (the origin the backend's CORS allows). The API lives at VITE_API_BASE (default :8000).
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, strictPort: true },
})
