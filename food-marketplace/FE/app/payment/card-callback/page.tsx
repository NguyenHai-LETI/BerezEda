'use client'

import { useEffect } from 'react'

export default function CardCallbackPage() {
  useEffect(() => {
    // Notify the opener (card list page) that a card was registered
    if (window.opener) {
      window.opener.postMessage({ type: 'CARD_REGISTERED' }, window.location.origin)
    }
    // Close this tab — works because this window was opened via window.open()
    window.close()
  }, [])

  return (
    <div className="flex flex-col items-center justify-center h-screen bg-white gap-4 px-6 text-center">
      <div className="text-5xl">✅</div>
      <h1 className="text-xl font-bold text-gray-900">Карта успешно добавлена!</h1>
      <p className="text-sm text-gray-500">Вкладка закроется автоматически. Если нет — закройте её вручную.</p>
    </div>
  )
}
