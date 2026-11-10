import process from 'node:process'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { configurarServidorLocal } from './config/proxyApiLocal.mjs'

export default defineConfig(({ command }) => {
  const server = configurarServidorLocal(command, process.env)
  return {
    plugins: [react()],
    ...(server ? { server } : {}),
  }
})
