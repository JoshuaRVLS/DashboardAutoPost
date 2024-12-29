import "./globals.css";
import AuthProvider from "@/providers/AuthProvider";
import { Toaster } from "react-hot-toast";

export default function RootLayout({ children, session }) {
  return (
    <html lang="en">
      <body className={`antialiased`}>
        <AuthProvider session={session}>
          <Toaster
            toastOptions={{
              className: "toast",
              style: {
                background: "#1e2124",
                color: "gray",
              },
            }}
            position="top-center"
          />
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}
