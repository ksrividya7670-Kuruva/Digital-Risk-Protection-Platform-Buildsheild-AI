import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "BrandShield AI | Digital Risk Protection",
    template: "%s | BrandShield AI",
  },
  description:
    "Digital Risk Protection Platform for social profile and mobile app threat monitoring.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
