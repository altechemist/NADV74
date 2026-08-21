// Holds the signed-in user and the login/register/logout actions.
import { createContext, useContext, useEffect, useState } from "react";
import { api } from "../api/csrms";
import { tokenStore } from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // On first load, exchange a stored access token for the profile.
  useEffect(() => {
    if (!tokenStore.access) {
      setLoading(false);
      return;
    }
    api
      .me()
      .then(setUser)
      .catch(() => tokenStore.clear())
      .finally(() => setLoading(false));
  }, []);

  async function login(username, password) {
    const payload = await api.login(username, password);
    tokenStore.save(payload.access, payload.refresh);
    setUser(payload.user);
    return payload.user;
  }

  async function register(payload) {
    // Registration always creates a student account server-side.
    const created = await api.register(payload);
    // Sign straight in so the new student lands on their dashboard.
    return login(payload.username, payload.password);
  }

  async function logout() {
    try {
      await api.logout(tokenStore.refresh);
    } finally {
      tokenStore.clear();
      setUser(null);
    }
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
