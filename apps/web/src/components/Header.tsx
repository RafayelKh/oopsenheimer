import Link from "next/link";
import { BackendStatus } from "@/components/BackendStatus";
import "./components.css";

export function Header() {
  return (
    <header className="header">
      <Link href="/" className="brand">
        <span className="brand-mark" />
        <span>Oops-enheimer</span>
      </Link>
      <nav className="header-nav" aria-label="Primary">
        <BackendStatus />
        <Link href="/">Workbench</Link>
      </nav>
    </header>
  );
}
