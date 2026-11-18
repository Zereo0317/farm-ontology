import { Link, type LinkProps } from "@tanstack/react-router";
import type { ComponentProps } from "react";

export type Variant = "primary" | "secondary" | "inverse" | "ghost";

const base =
  "inline-flex min-h-11 items-center justify-center rounded-control px-5 py-2.5 text-center text-sm font-medium leading-snug transition-[scale,background-color,opacity] duration-150 ease-out active:not-disabled:scale-[0.96] disabled:cursor-not-allowed disabled:opacity-50";

const styles: Record<Variant, string> = {
  primary: "bg-ink text-paper hover:opacity-90",
  secondary: "border border-line bg-transparent text-ink hover:bg-paper-2",
  inverse: "bg-paper text-ink hover:bg-paper-2",
  ghost: "bg-transparent px-0 text-ink underline-offset-4 hover:underline",
};

export function buttonClass(variant: Variant = "primary", className = "") {
  return `${base} ${styles[variant]} ${className}`;
}

export function Button({
  variant = "primary",
  className = "",
  type = "button",
  ...props
}: ComponentProps<"button"> & { variant?: Variant }) {
  return <button type={type} className={buttonClass(variant, className)} {...props} />;
}

export function ButtonLink({
  variant = "primary",
  className = "",
  ...props
}: LinkProps & { variant?: Variant; className?: string }) {
  return <Link className={buttonClass(variant, className)} {...props} />;
}
