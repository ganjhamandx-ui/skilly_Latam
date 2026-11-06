// LCOV nativo de Node: no convierte ni inventa contadores V8/JSX.
import fs from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { spawnSync } from 'node:child_process'
import * as reporters from 'node:test/reporters'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..')
const backup = path.resolve(root, '..', 'SKILLY_recuperacion_edc8ec3a8e2e46cf940417c815a04d2b')
const output = process.argv[2]
if (!output || !path.isAbsolute(output)) throw new Error('Se requiere una carpeta absoluta nueva de evidencia')
const resolved = path.resolve(output)
if (!resolved.toLowerCase().startsWith((backup + path.sep).toLowerCase())) throw new Error('La evidencia debe quedar bajo el respaldo externo')
if (typeof reporters.lcov !== 'function') throw new Error('Este Node no dispone del reporter LCOV nativo')
await fs.mkdir(resolved)
const frontend = path.join(root, 'frontend')
const tests = (await fs.readdir(path.join(frontend, 'tests')))
  .filter(name => name.endsWith('.test.mjs')).sort()
  .map(name => path.join(frontend, 'tests', name))
const lcov = path.join(resolved, 'lcov.info')
const run = spawnSync(process.execPath, [
  '--test', '--experimental-test-coverage', '--test-coverage-include=frontend/src/**',
  '--test-reporter=spec', '--test-reporter-destination=stdout',
  '--test-reporter=lcov', `--test-reporter-destination=${lcov}`, ...tests,
], { cwd: root, encoding: 'utf8', timeout: 120000, windowsHide: true })
await fs.writeFile(path.join(resolved, 'tests.log'), (run.stdout || '') + (run.stderr || ''))
const text = await fs.readFile(lcov, 'utf8')
const sources = [...text.matchAll(/^SF:(.+)$/gm)].map(match => match[1])
if (!sources.length) throw new Error('No se generaron contadores LCOV de archivos fuente')
const result = {
  node_version: process.version, exit_code: run.status, test_files: tests.length,
  tests: Number((run.stdout || '').match(/\btests (\d+)/)?.[1] || 0),
  passed: Number((run.stdout || '').match(/\bpass (\d+)/)?.[1] || 0),
  failed: Number((run.stdout || '').match(/\bfail (\d+)/)?.[1] || 0),
  coverage_source: 'Native node:test coverage and LCOV reporter', sources,
  report: lcov, browser_or_jsx_coverage_claimed: false,
  limitation: 'Only modules imported by these Node tests are measured; unimported JSX is not covered.',
}
await fs.writeFile(path.join(resolved, 'resultado.json'), JSON.stringify(result, null, 2))
console.log(JSON.stringify(result))
process.exitCode = run.status === 0 ? 0 : 1
