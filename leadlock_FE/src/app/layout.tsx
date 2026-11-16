import type { Metadata } from 'next';
import './globals.css';
import { Sidebar } from '@/components/Sidebar';

export const metadata: Metadata = {
  title: 'LeadLock AI — Conversational Automation Dashboard',
  description:
    'Multi-tenant AI-powered WhatsApp automation platform for lead management, live chat monitoring, and inventory control.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>
        <div style={{ display: 'flex', minHeight: '100vh' }}>
          <Sidebar />
          <main
            style={{
              marginLeft: '260px',
              flex: 1,
              padding: '2rem',
              minHeight: '100vh',
            }}
          >
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
