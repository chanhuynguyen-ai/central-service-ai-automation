import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CentralOps AI | Service Automation",
  description:
    "AI-powered employee request triage, approval automation, operational analytics, and policy assistance.",
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
