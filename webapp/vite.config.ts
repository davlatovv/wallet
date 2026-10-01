import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Vite's dev server rejects unrecognized Host headers by default
    // (CVE-2023-xxxx-style DNS-rebinding protection). Needed to open this
    // through a dev tunnel (ngrok/cloudflared — see docs/MINIAPP_PLAN.md
    // task 0.4 and webapp/README.md), whose hostname is random each run.
    // Dev-server only: `vite build` (the real production artifact) never
    // reads this.
    allowedHosts: true,
  },
})
