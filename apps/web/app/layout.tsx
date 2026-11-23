import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Acme HR & IT Assistant",
  description: "Enterprise HR and IT Helpdesk Assistant for Acme Corporation",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased min-h-screen bg-slate-50 flex flex-col">
        {children}
      </body>
    </html>
  );
}
