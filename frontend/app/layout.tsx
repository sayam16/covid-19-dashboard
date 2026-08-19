import type { Metadata } from "next";

import "./globals.css";

import { SidebarNav } from "@/components/layout/sidebar-nav";
import { Topbar } from "@/components/layout/topbar";

export const metadata: Metadata = {
  title: "COVID Signal Studio",
  description: "Interactive COVID-19 analytics dashboard with hybrid forecasting and trend detection."
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="font-sans">
        <div className="mx-auto flex min-h-screen max-w-[1600px]">
          <SidebarNav />
          <main className="w-full flex-1 px-4 py-4 lg:px-8 lg:py-8">
            <Topbar />
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
