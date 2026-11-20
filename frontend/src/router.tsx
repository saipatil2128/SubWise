import { Navigate, type RouteObject } from "react-router";

import { AppLayout } from "./components/Layout";
import { LoginPage, RegisterPage } from "./pages/Auth";
import { ComparePage } from "./pages/Compare";
import { DashboardPage } from "./pages/Dashboard";
import { HistoryPage } from "./pages/History";
import { LandingPage } from "./pages/Landing";
import { NotFoundPage } from "./pages/NotFound";
import { OptimizerPage } from "./pages/Optimizer";
import { PlansPage } from "./pages/Plans";
import { ReportPage } from "./pages/ReportPage";
import { RunPage } from "./pages/RunPage";
import { SettingsPage } from "./pages/Settings";
import { SubscriptionsPage } from "./pages/Subscriptions";

export const routes: RouteObject[] = [
  { path: "/", element: <LandingPage /> },
  { path: "/login", element: <LoginPage /> },
  { path: "/register", element: <RegisterPage /> },
  {
    path: "/app",
    element: <AppLayout />,
    children: [
      { index: true, element: <DashboardPage /> },
      { path: "subscriptions", element: <SubscriptionsPage /> },
      { path: "optimize", element: <OptimizerPage /> },
      { path: "runs/:runId", element: <RunPage /> },
      { path: "reports/:reportId", element: <ReportPage /> },
      { path: "plans", element: <PlansPage /> },
      { path: "compare", element: <ComparePage /> },
      { path: "history", element: <HistoryPage /> },
      { path: "settings", element: <SettingsPage /> },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
  { path: "/dashboard", element: <Navigate to="/app" replace /> },
  { path: "*", element: <NotFoundPage /> },
];
