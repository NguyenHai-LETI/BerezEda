'use client'

import { useState } from 'react'
import dynamic from 'next/dynamic'
import { validateQR, confirmDeposit, confirmPickup, type ValidateQRResponse } from '@/lib/api'
import { Camera, CheckCircle, XCircle, Package, ShoppingBag, RefreshCw } from 'lucide-react'

const QRScanner = dynamic(() => import('./QRScanner'), { ssr: false })

type SimState = 'idle' | 'scanning' | 'validating' | 'valid_aa' | 'valid_bb' | 'invalid' | 'action_done' | 'action_error'

export default function LockerSimulator() {
  const [simState, setSimState] = useState<SimState>('idle')
  const [scanResult, setScanResult] = useState<ValidateQRResponse | null>(null)
  const [actionMsg, setActionMsg] = useState('')
  const [actionLoading, setActionLoading] = useState(false)

  function startScan() {
    setScanResult(null)
    setActionMsg('')
    setSimState('scanning')
  }

  function reset() {
    setScanResult(null)
    setActionMsg('')
    setSimState('idle')
  }

  async function handleQRScan(code: string) {
    setSimState('validating')
    try {
      const res = await validateQR(code)
      setScanResult(res)
      if (res.valid && res.code_type === 'AA') setSimState('valid_aa')
      else if (res.valid && res.code_type === 'BB') setSimState('valid_bb')
      else setSimState('invalid')
    } catch {
      setScanResult({ valid: false, message: 'Lỗi kết nối server' })
      setSimState('invalid')
    }
  }

  async function handleDeposit() {
    if (!scanResult?.code) return
    setActionLoading(true)
    try {
      const res = await confirmDeposit(scanResult.code)
      setActionMsg(res.message)
      setSimState('action_done')
    } catch (e: any) {
      setActionMsg(e.message || 'Lỗi xác nhận')
      setSimState('action_error')
    } finally {
      setActionLoading(false)
    }
  }

  async function handlePickup() {
    if (!scanResult?.code) return
    setActionLoading(true)
    try {
      const res = await confirmPickup(scanResult.code)
      setActionMsg(res.message)
      setSimState('action_done')
    } catch (e: any) {
      setActionMsg(e.message || 'Lỗi xác nhận')
      setSimState('action_error')
    } finally {
      setActionLoading(false)
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center gap-2 mb-4">
        <h2 className="text-xl font-bold text-gray-800">Симулятор постамата</h2>
      </div>

      {/* Simulator Screen */}
      <div className="flex-1 bg-gray-900 rounded-2xl p-4 flex flex-col text-white overflow-hidden">

        {/* Idle */}
        {simState === 'idle' && (
          <div className="flex-1 flex flex-col items-center justify-center gap-4">
            <div className="w-20 h-20 rounded-2xl bg-gray-700 flex items-center justify-center">
              <Camera className="h-10 w-10 text-gray-400" />
            </div>
            <div className="text-center">
              <p className="text-lg font-bold text-gray-200">Готов к сканированию</p>
              <p className="text-sm text-gray-500 mt-1">Нажмите кнопку для открытия камеры</p>
            </div>
            <button
              onClick={startScan}
              className="mt-2 bg-green-600 hover:bg-green-500 text-white font-bold px-8 py-3 rounded-xl transition text-base"
            >
              Сканировать QR-код
            </button>
          </div>
        )}

        {/* Scanning */}
        {simState === 'scanning' && (
          <div className="flex-1 flex flex-col">
            <p className="text-sm text-gray-400 text-center mb-2">Наведите камеру на QR-код</p>
            <div className="flex-1 min-h-0">
              <QRScanner onScan={handleQRScan} active={simState === 'scanning'} />
            </div>
            <button
              onClick={reset}
              className="mt-3 text-gray-500 hover:text-gray-300 text-sm text-center"
            >
              Отмена
            </button>
          </div>
        )}

        {/* Validating */}
        {simState === 'validating' && (
          <div className="flex-1 flex flex-col items-center justify-center gap-3">
            <div className="h-10 w-10 border-4 border-green-500 border-t-transparent rounded-full animate-spin" />
            <p className="text-gray-300">Проверка QR-кода...</p>
          </div>
        )}

        {/* Invalid */}
        {simState === 'invalid' && (
          <div className="flex-1 flex flex-col items-center justify-center gap-4">
            <XCircle className="h-16 w-16 text-red-400" />
            <div className="text-center">
              <p className="text-lg font-bold text-red-400">QR-код недействителен</p>
              <p className="text-sm text-gray-500 mt-1">{scanResult?.message}</p>
            </div>
            <button onClick={reset} className="flex items-center gap-2 bg-gray-700 hover:bg-gray-600 px-6 py-2 rounded-xl text-sm">
              <RefreshCw className="h-4 w-4" /> Попробовать снова
            </button>
          </div>
        )}

        {/* Valid AA — deposit */}
        {simState === 'valid_aa' && (
          <div className="flex-1 flex flex-col items-center justify-center gap-4">
            <div className="w-16 h-16 bg-green-600 rounded-full flex items-center justify-center">
              <CheckCircle className="h-9 w-9 text-white" />
            </div>
            <div className="text-center">
              <p className="text-lg font-bold text-green-400">Код AA — Размещение товара</p>
              <p className="text-sm text-gray-400 mt-1">Код: <span className="font-mono text-white">{scanResult?.code}</span></p>
            </div>
            <div className="bg-gray-800 rounded-xl p-3 w-full text-xs text-gray-400 space-y-1">
              <p>Тип: <span className="text-yellow-300 font-semibold">AA — Размещение товара</span></p>
              {scanResult?.combo_id && <p>Combo: <span className="text-white font-mono">{scanResult.combo_id.slice(0, 8)}...</span></p>}
            </div>
            <div className="text-center text-gray-500 text-xs">Ячейка открыта. Пожалуйста, разместите товар внутри.</div>
            <button
              onClick={handleDeposit}
              disabled={actionLoading}
              className="w-full bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white font-bold py-4 rounded-xl text-base flex items-center justify-center gap-2 transition"
            >
              <Package className="h-5 w-5" />
              {actionLoading ? 'Обработка...' : 'Подтвердить размещение товара'}
            </button>
            <button onClick={reset} className="text-gray-600 hover:text-gray-400 text-sm">Отмена</button>
          </div>
        )}

        {/* Valid BB — pickup */}
        {simState === 'valid_bb' && (
          <div className="flex-1 flex flex-col items-center justify-center gap-4">
            <div className="w-16 h-16 bg-purple-600 rounded-full flex items-center justify-center">
              <CheckCircle className="h-9 w-9 text-white" />
            </div>
            <div className="text-center">
              <p className="text-lg font-bold text-purple-400">Код BB — Получение товара</p>
              <p className="text-sm text-gray-400 mt-1">Код: <span className="font-mono text-white">{scanResult?.code}</span></p>
            </div>
            <div className="bg-gray-800 rounded-xl p-3 w-full text-xs text-gray-400 space-y-1">
              <p>Тип: <span className="text-purple-300 font-semibold">BB — Получение товара</span></p>
              {scanResult?.order_id && <p>Заказ: <span className="text-white font-mono">{scanResult.order_id.slice(0, 8)}...</span></p>}
            </div>
            <div className="text-center text-gray-500 text-xs">Ячейка открыта. Заберите ваш товар.</div>
            <button
              onClick={handlePickup}
              disabled={actionLoading}
              className="w-full bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-white font-bold py-4 rounded-xl text-base flex items-center justify-center gap-2 transition"
            >
              <ShoppingBag className="h-5 w-5" />
              {actionLoading ? 'Обработка...' : 'Подтвердить получение товара'}
            </button>
            <button onClick={reset} className="text-gray-600 hover:text-gray-400 text-sm">Отмена</button>
          </div>
        )}

        {/* Action done */}
        {simState === 'action_done' && (
          <div className="flex-1 flex flex-col items-center justify-center gap-4">
            <div className="text-6xl">🔓</div>
            <div className="text-center">
              <p className="text-xl font-bold text-green-400">Успешно!</p>
              <p className="text-sm text-gray-400 mt-2">{actionMsg}</p>
            </div>
            <div className="bg-green-900/40 border border-green-700 rounded-xl p-3 text-center text-sm text-green-300">
              Статус обновлён и синхронизирован с Firebase
            </div>
            <button
              onClick={reset}
              className="bg-gray-700 hover:bg-gray-600 text-white font-semibold px-6 py-3 rounded-xl transition flex items-center gap-2"
            >
              <RefreshCw className="h-4 w-4" /> Сканировать другой код
            </button>
          </div>
        )}

        {/* Action error */}
        {simState === 'action_error' && (
          <div className="flex-1 flex flex-col items-center justify-center gap-4">
            <XCircle className="h-16 w-16 text-red-400" />
            <div className="text-center">
              <p className="text-lg font-bold text-red-400">Ошибка выполнения</p>
              <p className="text-sm text-gray-400 mt-1">{actionMsg}</p>
            </div>
            <button onClick={reset} className="flex items-center gap-2 bg-gray-700 hover:bg-gray-600 px-6 py-2 rounded-xl text-sm">
              <RefreshCw className="h-4 w-4" /> Попробовать снова
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
