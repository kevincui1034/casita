import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Casita — Livability Map",
  description:
    "SF + Marin rental listings ranked by dog policy, walkability, and neighborhood livability.",
  robots: { index: false, follow: false },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
