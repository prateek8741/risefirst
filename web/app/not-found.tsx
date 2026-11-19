import Link from "next/link";

export default function NotFound() {
  return (
    <div className="mx-auto max-w-lg card border-dashed p-10 text-center">
      <p className="font-mono text-5xl font-bold text-orange">404</p>
      <h1 className="mt-3 text-xl font-bold text-ink">This job isn&apos;t available</h1>
      <p className="mt-2 text-muted">It may have been filled or removed by the employer.</p>
      <Link href="/" className="btn btn-primary mt-6">Browse open jobs →</Link>
    </div>
  );
}
