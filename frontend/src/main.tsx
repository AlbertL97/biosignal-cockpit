import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, HashRouter } from "react-router-dom";
import App from "./App";
import { IS_DEMO } from "./api/client";
import "./index.css";

// HashRouter in the static demo avoids GitHub Pages deep-link 404s; the live
// app (with a backend) uses BrowserRouter.
const Router = IS_DEMO ? HashRouter : BrowserRouter;

const root = document.getElementById("root");
if (!root) throw new Error("Root element #root not found");

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

ReactDOM.createRoot(root).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <Router>
        <App />
      </Router>
    </QueryClientProvider>
  </React.StrictMode>,
);
