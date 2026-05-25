/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    remotePatterns: [
      { protocol: 'http', hostname: 'localhost' },
      { protocol: 'https', hostname: 'ui-avatars.com' },
    ],
  },
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api',
    NEXT_PUBLIC_FIREBASE_API_KEY: 'AIzaSyCXoP3dDsEKdO5HgpTt8AWrXNaupIbLjSQ',
    NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN: 'food-marketplace-192f7.firebaseapp.com',
    NEXT_PUBLIC_FIREBASE_PROJECT_ID: 'food-marketplace-192f7',
    NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET: 'food-marketplace-192f7.appspot.com',
    NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID: '680705838341',
    NEXT_PUBLIC_FIREBASE_APP_ID: '1:680705838341:web:62b3da01a6f90c95613b6c',
    NEXT_PUBLIC_FIREBASE_VAPID_KEY: 'BKijJyffVzTrwhzKl_CBIy6YwbvbzR-6ne3Hz9fKRYkhm9JQ-XLaSRI7QS87rCnxmHyaSGdMhBknjbDE2MaSEPs',
  },
}

module.exports = nextConfig
