import type { RouteObject } from "react-router";

import { Layout } from "./App";
import {
  DashboardPage,
  HistoryPage,
  LoginPage,
  OptimizerPage,
  PricesPage,
  ProfilePage,
  SubscriptionsPage,
} from "./pages";

export const routes: RouteObject[] = [
  { path: "/login", element: <LoginPage /> },
  {
    path: "/",
    element: <Layout />,
    children: [
      { index: true, element: <DashboardPage /> },
      { path: "subscriptions", element: <SubscriptionsPage /> },
      { path: "optimizer/:threadId?", element: <OptimizerPage /> },
      { path: "prices", element: <PricesPage /> },
      { path: "history", element: <HistoryPage /> },
      { path: "profile", element: <ProfilePage /> },
    ],
  },
];
