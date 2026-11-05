import test from 'node:test'
import assert from 'node:assert/strict'
import { mostrarAvisoPolitica, claveAvisoPolitica } from '../src/avisoPoliticaCancelacionE3.mjs'
const base={referencia:'referencia-valida',habilitarFormulario:true,cargando:false,politica:{aceptada:false,contrato_previo:false,version:'v1',texto:'Condiciones completas'}}
test('muestra aviso tras publicar condiciones y habilitar pago',()=>assert.equal(mostrarAvisoPolitica(base),true))
test('no abre modal antes de comunicar condiciones',()=>assert.equal(mostrarAvisoPolitica({...base,habilitarFormulario:false}),false))
test('no abre modal antes de cargar la consulta',()=>assert.equal(mostrarAvisoPolitica({...base,cargando:true}),false))
test('no abre modal a un contrato ya aceptado',()=>assert.equal(mostrarAvisoPolitica({...base,politica:{...base.politica,aceptada:true}}),false))
test('respeta contratos de pago previos',()=>assert.equal(mostrarAvisoPolitica({...base,politica:{...base.politica,contrato_previo:true}}),false))
test('no presenta una política sin versión o texto',()=>{assert.equal(mostrarAvisoPolitica({...base,politica:{...base.politica,version:''}}),false);assert.equal(mostrarAvisoPolitica({...base,politica:{...base.politica,texto:''}}),false)})
test('distingue revisiones de política para la misma referencia',()=>assert.notEqual(claveAvisoPolitica('a','v1'),claveAvisoPolitica('a','v2')))
test('distingue dos organizaciones',()=>assert.notEqual(claveAvisoPolitica('a','v1'),claveAvisoPolitica('b','v1')))
