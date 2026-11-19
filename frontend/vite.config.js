// Activa el proxy local solo al servir la aplicación. La compilación omite esa configuración.
import process from 'node:process'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { configurarServidorLocal } from './config/proxyApiLocal.mjs'

// El proxy local solo se habilita en desarrollo y valida el destino de la API.
export default defineConfig(({ command }) => {
  const server = configurarServidorLocal(command, process.env)
  return {
    plugins: [react()],
    ...(server ? { server } : {}),
  }
})
