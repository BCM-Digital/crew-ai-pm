import type { Metadata } from "next"
import "./globals.css"

export const metadata: Metadata = {
  title: "PM Agent Dashboard",
  description: "Monitor and interact with the crew",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}