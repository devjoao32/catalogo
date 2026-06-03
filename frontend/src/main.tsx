import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import App from "./App";
import ErpAdminPage from "./components/ErpAdminPage";
import RepresentativeGuard from "./components/RepresentativeGuard";
import RepresentativeLoginPage from "./components/RepresentativeLoginPage";
import "./styles.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<RepresentativeLoginPage />} />
          <Route
            path="/"
            element={
              <RepresentativeGuard>
                <App />
              </RepresentativeGuard>
            }
          />
          <Route path="/erp" element={<ErpAdminPage />} />
          <Route
            path="/produto/:productId"
            element={
              <RepresentativeGuard>
                <App />
              </RepresentativeGuard>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>
);
