import type { Metadata } from "next";
import "./globals.css";
import NotificationInit from '@/components/NotificationInit';
import { I18nProvider } from '@/contexts/I18nContext';
import { Manrope, JetBrains_Mono } from 'next/font/google';

const manrope = Manrope({
  subsets: ['latin', 'cyrillic'],
  weight: ['400', '500', '600', '700', '800'],
  variable: '--font-manrope',
  display: 'swap',
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  weight: ['400', '500'],
  variable: '--font-jetbrains',
  display: 'swap',
});

export const metadata: Metadata = {
  title: "БережЕда",
  description: "Спасайте еду — покупайте наборы со скидкой",
  icons: {
    icon: "/icon.svg",
    apple: "/icon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ru" className={`${manrope.variable} ${jetbrainsMono.variable}`}>
      <body>
        <I18nProvider>
          <NotificationInit />
          {children}
        </I18nProvider>
      </body>
    </html>
  );
}
