import type { Metadata } from "next";
import "./globals.css";
import { Header } from "@/components/Header";

export const metadata: Metadata = {
  title: "Oosenhaimer",
  description: "Վոքսելային ճառագայթման սիմուլյացիայի միջավայր",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="hy">
      <body>
        <div className="app-shell">
          <Header />
          {children}
        </div>
      </body>
    </html>
  );
}
