import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), 'VITE_');
  return {
    // GitHub Pages project sites live under /<repository-name>/.
    // Keep '/' as the default for local development and other root-hosted deployments.
    base: env.VITE_BASE_PATH || '/',
    plugins: [react()],
    server: { port: 5173 },
  };
});
