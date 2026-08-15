import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { ClerkProvider } from "@clerk/clerk-react";
import App from "./App.jsx";
import "./styles.css";

const PUBLISHABLE_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;

const root = ReactDOM.createRoot(document.getElementById("root"));

if (!PUBLISHABLE_KEY) {
  // Fail loudly and legibly rather than throwing an opaque Clerk error.
  root.render(
    <div style={{ padding: 40, fontFamily: "system-ui, sans-serif" }}>
      <h1>Missing Clerk key</h1>
      <p>Set <code>VITE_CLERK_PUBLISHABLE_KEY</code> in <code>frontend/.env</code>, then
        restart the dev server. Vite only reads env files at startup.
      </p>
    </div>
  );
} else {
  root.render(
    <React.StrictMode>
      <ClerkProvider publishableKey={PUBLISHABLE_KEY} afterSignOutUrl="/">
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </ClerkProvider>
    </React.StrictMode>
  );
}
