// ============================================================
// pages/_app.js
// Global Next.js app wrapper.
// Sets up global styles and Toaster for notifications.
// ============================================================

import "../styles/globals.css";
import { Toaster } from "react-hot-toast";

export default function App({ Component, pageProps }) {
  return (
    <>
      {/* Global toast notification provider */}
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            borderRadius: "10px",
            background: "#1f2937",
            color: "#f9fafb",
            fontSize: "14px",
          },
          success: {
            iconTheme: { primary: "#10b981", secondary: "#f9fafb" },
          },
          error: {
            iconTheme: { primary: "#ef4444", secondary: "#f9fafb" },
          },
        }}
      />
      <Component {...pageProps} />
    </>
  );
}