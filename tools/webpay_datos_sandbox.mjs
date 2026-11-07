// Extrae exclusivamente el ejemplo de aprobacion y autenticacion de pruebas.
// No hace red, no lee configuracion local y nunca imprime los valores obtenidos.
const normalize = text => text.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase()
const plain = text => text.replace(/<[^>]*>/g, ' ').replace(/&nbsp;/gi, ' ').replace(/[*`_]/g, '')

export function datosSandboxDesdeDocumentacion(document) {
  const text = typeof document === 'string' ? normalize(document) : ''
  const sectionStart = text.indexOf('tarjetas de prueba')
  const section = sectionStart >= 0 ? text.slice(sectionStart) : ''
  const row = section.match(/^\s*\|?\s*visa\s*\|\s*(.+)$/im)?.[1] || ''
  const rowText = plain(row)
  const authentication = (section.match(/cuando aparece un formulario de autenticacion[\s\S]*?(?=\r?\n\s*#{1,6}\s|\r?\n\s*\r?\n|$)/i)?.[0] || '').slice(0, 1000).trim()
  const authenticationText = plain(authentication)
  const pan = rowText.match(/\b(?:\d[ -]?){15}\d\b/)?.[0]?.replace(/\D/g, '')
  const cvv = rowText.match(/\bcvv\s*[:\-]?\s*(\d{3,4})\b/i)?.[1]
  const rut = authenticationText.match(/\brut\s+(\d[\d.]*-[\dk])\b/i)?.[1]
  const password = authenticationText.match(/\bclave\s+(\d{3,12})\b/i)?.[1]
  const metadata = {
    section_found: sectionStart >= 0, visa_row_found: !!row,
    visa_row_approved: /genera\s+transacciones\s+aprobadas/.test(rowText),
    authentication_paragraph_found: !!authentication,
    authentication_multiline: /[\r\n]/.test(authentication),
    pan_found: !!pan, cvv_found: !!cvv, rut_found: !!rut, password_found: !!password,
  }
  let code = null
  if (!metadata.section_found) code = 'OFFICIAL_DOCS_SECTION_MISSING'
  else if (!metadata.visa_row_found || !metadata.visa_row_approved) code = 'OFFICIAL_DOCS_VISA_ROW_INVALID'
  else if (!pan || !cvv) code = 'OFFICIAL_DOCS_CARD_FORMAT_INVALID'
  else if (!rut || !password) code = 'OFFICIAL_DOCS_AUTH_FORMAT_INVALID'
  return { metadata, code, data: code ? null : { pan, cvv, rut, password } }
}
