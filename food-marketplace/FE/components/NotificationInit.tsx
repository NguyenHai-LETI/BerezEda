'use client'
import { useEffect, useRef } from 'react'
import { requestNotificationPermission, onForegroundMessage } from '@/lib/firebase'
import { registerDevice } from '@/lib/api'
import { getToken } from '@/lib/auth'

export default function NotificationInit() {
  const fcmRegistered = useRef(false)

  useEffect(() => {
    async function initFCM() {
      if (fcmRegistered.current) return
      if (!getToken()) return

      fcmRegistered.current = true

      const fcmToken = await requestNotificationPermission().catch(() => null)
      if (fcmToken) {
        try {
          await registerDevice(fcmToken)
        } catch (err) {
          console.error('[FCM] registerDevice failed:', err)
          fcmRegistered.current = false
        }
      }
    }

    initFCM()

    window.addEventListener('auth-changed', initFCM)
    return () => window.removeEventListener('auth-changed', initFCM)
  }, [])

  useEffect(() => {
    onForegroundMessage((payload) => {
      const { title, body } = payload.notification || {}
      if (!title || Notification.permission !== 'granted') return
      navigator.serviceWorker.ready.then(registration => {
        registration.showNotification(title, {
          body: body || '',
          data: payload.data || {},
        })
      })
    })
  }, [])

  return null
}
