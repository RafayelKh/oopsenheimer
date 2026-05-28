import Link from "next/link";
import { BackendStatus } from "@/components/BackendStatus";
import "./components.css";

export function Header() {
  return (
    <header className="header">
      <Link href="/" className="brand">
        <img aria-hidden="true" className="brand-logo" src="/oopsenheimer.svg" alt="" />
        <span>Oosenhaimer</span>
      </Link>
      <nav className="header-nav" aria-label="Հիմնական">
        <BackendStatus />
        <Link href="/">Աշխատասեղան</Link>
      </nav>
    </header>
  );
}
