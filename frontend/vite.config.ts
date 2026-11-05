import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"
import tailwindcss from "@tailwindcss/vite"

export default defineConfig({
  base: "./",
  plugins: [
    react(),
    tailwindcss(),
  ],
  build: {
    rollupOptions: {
      output: {
        format: 'iife',
        name: 'NetSpoutApp',
        inlineDynamicImports: true
      }
    }
  },
  server: {
    port: 5173,
    host: true,
    proxy: {
      "/api": {
        target: process.env.NETSPOUT_DEV_BACKEND ?? "http://localhost:8081",   // set NETSPOUT_DEV_BACKEND to an isolated engine when running browser tests; the default is the usual local engine
        changeOrigin: true
      },
      "/ws": {
        target: (process.env.NETSPOUT_DEV_BACKEND ?? "http://localhost:8081").replace(/^http/, "ws"),
        ws: true
      }
    }
  }
})
