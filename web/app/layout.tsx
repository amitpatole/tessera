import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Tessera — attested analytics",
  description:
    "Ask a finance question in plain English. Get the number, the SQL, an independent verdict, and a signed receipt.",
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
        </footer>
      </body>
    </html>
  );
}
