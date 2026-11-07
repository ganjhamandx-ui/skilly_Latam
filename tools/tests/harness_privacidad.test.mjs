// Pruebas negativas de los CLIs: ningun JSON privado corrupto debe filtrarse.
// No necesita servidor, PostgreSQL ni datos reales: el parseo falla antes de red.
import assert from 'node:assert/strict'
import { spawnSync } from 'node:child_process'
import { randomBytes } from 'node:crypto'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { test } from 'node:test'
import { fileURLToPath } from 'node:url'

const tools = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')

for (const driver of ['e2e_browser_aislado.mjs', 'e2e_webpay_sandbox_aislado.mjs']) {
  test(`${driver}: error de JSON privado no revela fragmentos ni stack`, () => {
    const temporary = fs.mkdtempSync(path.join(os.tmpdir(), 'skilly-cli-privacy-'))
    const context = path.join(temporary, 'contexto.json')
    const canary = randomBytes(36).toString('hex')
    try {
      // Se corta el JSON dentro del dato para que un SyntaxError sin capturar
      // pudiera mostrar un fragmento privado. El canario nunca se imprime.
      fs.writeFileSync(context, '{"private_fixture":"' + canary, { flag: 'wx' })
      const child = spawnSync(process.execPath, [path.join(tools, driver), context], {
        encoding: 'utf8', timeout: 15000, windowsHide: true,
        env: { ...process.env, NODE_OPTIONS: '' },
      })
      assert.ifError(child.error)
      assert.equal(child.status, 1, 'El CLI debe detenerse antes de arrancar el entorno')
      const stdout = child.stdout || '', stderr = child.stderr || ''
      assert.ok(!stdout.includes(canary) && !stderr.includes(canary), 'Se filtro el canario privado')
      assert.ok(!stdout.includes('private_fixture') && !stderr.includes('private_fixture'), 'Se filtro un fragmento del JSON')
      assert.equal(stderr.trim(), '', 'El CLI no debe imprimir un stack ni error sin sanitizar')
      const result = JSON.parse(stdout.trim())
      assert.equal(result.completed, false)
      assert.equal(result.error_type, 'SyntaxError')
      assert.ok(!Object.hasOwn(result, 'message') && !Object.hasOwn(result, 'stack'), 'El resumen debe limitarse al tipo de error')
    } finally {
      // Solo se retiran los dos elementos creados por esta prueba, sin recorrido.
      if (fs.existsSync(context)) fs.unlinkSync(context)
      fs.rmdirSync(temporary)
    }
  })
}
