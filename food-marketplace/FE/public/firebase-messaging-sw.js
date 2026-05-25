importScripts('https://www.gstatic.com/firebasejs/10.7.1/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/10.7.1/firebase-messaging-compat.js');

firebase.initializeApp({
  apiKey: 'AIzaSyCXoP3dDsEKdO5HgpTt8AWrXNaupIbLjSQ',
  authDomain: 'food-marketplace-192f7.firebaseapp.com',
  projectId: 'food-marketplace-192f7',
  storageBucket: 'food-marketplace-192f7.appspot.com',
  messagingSenderId: '680705838341',
  appId: '1:680705838341:web:62b3da01a6f90c95613b6c',
});

const messaging = firebase.messaging();

messaging.onBackgroundMessage(function(payload) {
  const { title, body } = payload.notification || {};
  if (!title) return;
  self.registration.showNotification(title, {
    body: body || '',
    data: payload.data || {},
  });
});

self.addEventListener('notificationclick', function(event) {
  console.log('[SW] notificationclick fired, data:', JSON.stringify(event.notification.data));
  event.notification.close();
  const data = event.notification.data || {};
  let path = '/';
  if (data.combo_id) {
    path = '/combos/' + data.combo_id;
  } else if (data.order_id) {
    path = '/history';
  }
  const fullUrl = self.location.origin + path;
  console.log('[SW] navigating to:', fullUrl);
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function(clientList) {
      console.log('[SW] open clients:', clientList.length, clientList.map(function(c) { return c.url; }));
      for (const client of clientList) {
        if (client.url === fullUrl && 'focus' in client) {
          console.log('[SW] focusing existing tab');
          return client.focus();
        }
      }
      console.log('[SW] opening new window');
      return clients.openWindow(fullUrl);
    })
  );
});
