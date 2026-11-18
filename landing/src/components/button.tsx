import { Link, type LinkProps } from "@tanstack/react-router";
import type { ComponentProps } from "react";

export type Variant = "primary" | "secondary" | "inverse" | "ghost";

const base =
  "inline-flex min-h-12 items-center justify-center gap-2 rounded-full px-6 py-3 text-center text-sm font-medium leading-snug tracking-wide text-balance transition-[scale,background-color,opacity,box-shadow] duration-150 ease-out hover:shadow-[0_2px_10px_rgba(28,27,25,0.14)] active:not-disabled:scale-[0.97] disabled:cursor-not-allowed disabled:opacity-50 sm:px-7 sm:text-base";

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
