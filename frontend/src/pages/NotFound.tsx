import { Link } from "react-router";

export function NotFoundPage() {
  return (
    <div className="mx-auto max-w-md py-24 text-center">
      <p className="text-5xl font-semibold text-slate-300">404</p>
      <p className="mt-4 text-slate-700">This page doesn’t exist.</p>
      <Link to="/app" className="mt-6 inline-block text-sm font-medium text-indigo-600 hover:underline">
        Go to dashboard
      </Link>
    </div>
  );
}
