import { cn } from "@/lib/cn";

type FlashVariant = "success" | "error" | "info";

const VARIANT_CLASS: Record<FlashVariant, string> = {
  success: "border-green-200 bg-green-50 text-green-800",
  error: "border-red-200 bg-red-50 text-red-800",
  info: "border-blue-200 bg-blue-50 text-blue-800",
};

export function FlashAlert({
  children,
  variant = "info",
  className,
}: {
  children: React.ReactNode;
  variant?: FlashVariant;
  className?: string;
}) {
  return (
    <div className={cn("mb-4 rounded-md border px-4 py-3 text-sm", VARIANT_CLASS[variant], className)} role="alert">
      {children}
    </div>
  );
}
