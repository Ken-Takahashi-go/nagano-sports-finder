import type { Metadata } from 'next';
import Link from 'next/link';
import './globals.css';

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || 'https://nagano-sports-finder.vercel.app';
const SITE_NAME = '長野県公共施設ナビ';
const DEFAULT_DESCRIPTION =
  '長野市の公共テニスコート・サッカー場・フットサル場を横断検索。ナイター・人工芝・屋内・無料施設で絞り込み可能。31施設・92面のデータベース。';

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: `${SITE_NAME}｜公共スポーツ施設の横断検索`,
    template: `%s｜${SITE_NAME}`,
  },
  description: DEFAULT_DESCRIPTION,
  keywords: [
    '長野市', '長野県', 'テニスコート', 'サッカー場', 'フットサル', '公共施設',
    '人工芝', 'ナイター', '空き状況', '予約', '施設検索',
  ],
  authors: [{ name: SITE_NAME }],
  openGraph: {
    type: 'website',
    locale: 'ja_JP',
    url: SITE_URL,
    siteName: SITE_NAME,
    title: `${SITE_NAME}｜公共スポーツ施設の横断検索`,
    description: DEFAULT_DESCRIPTION,
  },
  twitter: {
    card: 'summary',
    title: `${SITE_NAME}｜公共スポーツ施設の横断検索`,
    description: DEFAULT_DESCRIPTION,
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      'max-image-preview': 'large',
      'max-snippet': -1,
    },
  },
  alternates: { canonical: SITE_URL },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ja">
      <body className="min-h-screen flex flex-col">
        <header className="bg-brand-600 text-white shadow-md">
          <div className="container mx-auto px-4 py-3 flex items-center justify-between max-w-6xl">
            <Link href="/" className="flex items-center gap-2 hover:opacity-90">
              <span className="text-xl font-bold">長野県公共施設ナビ</span>
              <span className="text-xs bg-brand-800 px-2 py-0.5 rounded">BETA</span>
            </Link>
            <nav className="flex items-center gap-4 text-sm">
              <Link href="/search" className="hover:underline">
                施設検索
              </Link>
              <Link href="/contact" className="hover:underline">
                お問い合わせ
              </Link>
            </nav>
          </div>
        </header>

        <main className="flex-1">{children}</main>

        <footer className="bg-gray-100 border-t border-gray-200 mt-12">
          <div className="container mx-auto px-4 py-6 max-w-6xl text-sm text-gray-600">
            <p className="mb-2">
              <strong>データ提供元</strong>:
              長野市公式ホームページ (
              <a
                href="https://www.city.nagano.nagano.jp/"
                target="_blank"
                rel="noopener noreferrer"
                className="text-brand-600 hover:underline"
              >
                www.city.nagano.nagano.jp
              </a>
              ) ／ まちかぎリモート
            </p>
            <p className="mb-3">
              本サイトの情報は最終確認時刻のスナップショットです。予約時は必ず公式サイトでご確認ください。
            </p>
            <div className="flex flex-wrap gap-4 text-xs text-gray-500 pt-2 border-t border-gray-200">
              <Link href="/contact" className="text-brand-700 hover:underline">
                お問い合わせ
              </Link>
              <span>© 2026 長野県公共施設ナビ (Beta)</span>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
