'use client'

import { useEffect, useRef, useState } from 'react'

interface QRScannerProps {
  onScan: (result: string) => void
  onError?: (err: string) => void
  active: boolean
}

export default function QRScanner({ onScan, onError, active }: QRScannerProps) {
  const scannerRef = useRef<any>(null)
  const [status, setStatus] = useState<'loading' | 'running' | 'error'>('loading')
  const [errorMsg, setErrorMsg] = useState('')

  useEffect(() => {
    if (!active) {
      if (scannerRef.current) {
        scannerRef.current.stop().catch(() => {}).finally(() => {
          scannerRef.current = null
        })
      }
      setStatus('loading')
      setErrorMsg('')
      return
    }

    let mounted = true

    import('html5-qrcode').then(async ({ Html5Qrcode }) => {
      if (!mounted) return

      const scanner = new Html5Qrcode('qr-reader-sim')
      scannerRef.current = scanner

      try {
        const cameras = await Html5Qrcode.getCameras()
        if (!mounted) return
        if (!cameras || cameras.length === 0) {
          setErrorMsg('Không tìm thấy camera')
          setStatus('error')
          return
        }
        // Prefer back camera
        const cam = cameras.find(c => /back|environment/i.test(c.label)) || cameras[0]
        await scanner.start(
          cam.id,
          { fps: 10, qrbox: { width: 220, height: 220 } },
          (decodedText: string) => {
            if (!mounted) return
            onScan(decodedText)
            scanner.stop().catch(() => {})
            scannerRef.current = null
          },
          () => {},
        )
        if (mounted) setStatus('running')
      } catch (err: any) {
        if (!mounted) return
        setErrorMsg(err?.message || 'Не удалось получить доступ к камере')
        setStatus('error')
      }
    })

    return () => {
      mounted = false
      if (scannerRef.current) {
        scannerRef.current.stop().catch(() => {})
        scannerRef.current = null
      }
    }
  }, [active])

  return (
    <div className="flex flex-col items-center w-full">
      <div id="qr-reader-sim" className="w-full rounded-xl overflow-hidden" />
      {active && status === 'loading' && (
        <div className="text-center text-gray-400 text-sm py-6">Запрос доступа к камере...</div>
      )}
      {status === 'error' && (
        <div className="text-center text-red-400 text-sm py-4 px-3">
          ⚠ {errorMsg || 'Ошибка камеры'}
        </div>
      )}
    </div>
  )
}
