import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "AI Prep Buddy",
  description: "AI interview prep coach — study assistant",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <nav className="flex gap-4 border-b border-neutral-200 p-3 text-sm dark:border-neutral-800">
          <a href="/" className="hover:underline">Study</a>
          <a href="/quiz" className="hover:underline">Quiz</a>
          <a href="/skills" className="hover:underline">Skills</a>
        </nav>
        {children}
      </body>
    </html>
  );
}
