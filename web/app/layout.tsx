import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Tessera — every number, proven",
  description:
    "Attested NL→analytics for regulated finance. Ask in plain English; get the number, the SQL, an independent verdict, and a signed receipt you verify offline. Deploy in your VPC or fully air-gapped.",
  openGraph: {
    title: "Tessera — every number, proven",
    description:
      "The trust layer for finance analytics: an independent per-answer verdict and a signed, auditor-verifiable receipt.",
    images: ["/og.png"],
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>
        {children}
        <footer className="footer">
          <span className="mark">— amitpatole</span>
          <nav>
            <a href="https://github.com/amitpatole/tessera">GitHub</a>
            <a href="#try">Try it</a>
            <a href="#demo">Demo</a>
          </nav>
        </footer>
      </body>
    </html>
  );
}
