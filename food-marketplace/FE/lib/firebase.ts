import { initializeApp, getApps } from 'firebase/app'
import { getFirestore } from 'firebase/firestore'
import { getMessaging, getToken, onMessage, isSupported } from 'firebase/messaging'

const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
  storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID,
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID,
}

export function getFirebaseApp() {
  if (getApps().length > 0) return getApps()[0]
  return initializeApp(firebaseConfig)
}

export function getFirestoreDb() {
  return getFirestore(getFirebaseApp())
}

export async function requestNotificationPermission(): Promise<string | null> {
  try {
    const supported = await isSupported()
    if (!supported) {
      console.warn('[FCM] Firebase Messaging not supported in this browser')
      return null
    }

    const permission = await Notification.requestPermission()
    if (permission !== 'granted') {
      console.warn('[FCM] Notification permission not granted:', permission)
      return null
    }

    if (!('serviceWorker' in navigator)) {
      console.warn('[FCM] Service Worker not supported')
      return null
    }

    // Register SW then wait until it's fully active before subscribing
    await navigator.serviceWorker.register(
      '/firebase-messaging-sw.js',
      { updateViaCache: 'none' }
    )
    const registration = await navigator.serviceWorker.ready

    const app = getFirebaseApp()
    const messaging = getMessaging(app)

    const token = await getToken(messaging, {
      vapidKey: process.env.NEXT_PUBLIC_FIREBASE_VAPID_KEY,
      serviceWorkerRegistration: registration,
    })

    if (!token) {
      console.warn('[FCM] getToken returned empty — check VAPID key and SW config')
      return null
    }

    return token
  } catch (err) {
    console.error('[FCM] requestNotificationPermission failed:', err)
    return null
  }
}

export function onForegroundMessage(callback: (payload: any) => void) {
  isSupported().then(supported => {
    if (!supported) return
    const app = getFirebaseApp()
    const messaging = getMessaging(app)
    onMessage(messaging, callback)
  })
}
