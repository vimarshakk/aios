import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "AIOS — AI Operating System",
  description: "Multi-agent AI OS with voice, vision, code execution, and browser automation.",
  keywords: ["AI", "assistant", "AIOS", "multi-agent", "Ollama", "GPT", "Claude"],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <head>
        <link rel="icon" href="/favicon.ico" />
      </head>
      <body className={`${inter.variable} font-sans antialiased bg-aios-bg text-aios-text`}>
        {children}
      </body>
    </html>
  );
}
