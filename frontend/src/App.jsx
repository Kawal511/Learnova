import { useEffect } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { SignedIn, SignedOut, useAuth } from "@clerk/clerk-react";
import * as api from "./api";
import AuthPage from "./pages/AuthPage.jsx";
import DeckLibrary from "./pages/DeckLibrary.jsx";
import Landing from "./pages/Landing.jsx";
import Studio from "./pages/Studio.jsx";

/**
 * Hands Clerk's `getToken` to the API client once, so every request carries a
 * fresh session JWT without each caller threading a token through.
 */
function AuthBridge({ children }) {
  const { getToken, isLoaded } = useAuth();

  useEffect(() => {
    api.setTokenGetter(async () => {
      try {
        return await getToken();
      } catch {
        return null;
      }
    });
  }, [getToken]);

  if (!isLoaded) return null;
  return children;
}

/** Sends signed-out visitors to /sign-in, remembering where they were headed. */
function Protected({ children }) {
  const location = useLocation();
  return (
    <>
      <SignedIn>{children}</SignedIn>
      <SignedOut>
        <Navigate to="/sign-in" replace state={{ from: location.pathname }} />
      </SignedOut>
    </>
  );
}

export default function App() {
  return (
    <AuthBridge>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/sign-in/*" element={<AuthPage mode="sign-in" />} />
        <Route path="/sign-up/*" element={<AuthPage mode="sign-up" />} />
        <Route
          path="/studio"
          element={
            <Protected>
              <Studio />
            </Protected>
          }
        />
        <Route
          path="/decks"
          element={
            <Protected>
              <DeckLibrary />
            </Protected>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthBridge>
  );
}
