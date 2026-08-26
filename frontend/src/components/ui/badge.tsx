import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const badgeVariants = cva(
  `
  inline-flex
  items-center
  justify-center
  gap-1.5

  whitespace-nowrap

  rounded-full

  border

  px-3
  py-1

  text-xs
  font-medium
  leading-none

  text-white

  transition-all
  duration-200

  select-none

  focus-visible:outline-none
  focus-visible:ring-2
  focus-visible:ring-[#4A3FD6]/25

  [&>svg]:h-3.5
  [&>svg]:w-3.5
  [&>svg]:shrink-0
  `,
  {
    variants: {
      variant: {
        default: `
          border-[#4A5568]
          bg-[#4A5568]
          text-white
        `,

        secondary: `
          border-[#64748B]
          bg-[#64748B]
          text-white
        `,

        success: `
          border-[#16A34A]
          bg-[#16A34A]
          text-white
        `,

        warning: `
          border-[#D97706]
          bg-[#D97706]
          text-white
        `,

        info: `
          border-[#2563EB]
          bg-[#2563EB]
          text-white
        `,

        system: `
          border-[#7C3AED]
          bg-[#7C3AED]
          text-white
        `,

        inactive: `
          border-[#6B7280]
          bg-[#6B7280]
          text-white
        `,

        destructive: `
          border-[#DC2626]
          bg-[#DC2626]
          text-white
        `,

        outline: `
          border-[#475569]
          bg-[#475569]
          text-white
        `,

        ghost: `
          border-[#475569]
          bg-[#475569]
          text-white
        `,

        link: `
          border-[#4A3FD6]
          bg-[#4A3FD6]
          text-white
        `,

        purple: `
          border-[#9333EA]
          bg-[#9333EA]
          text-white
        `,

        pink: `
          border-[#DB2777]
          bg-[#DB2777]
          text-white
        `,

        orange: `
          border-[#EA580C]
          bg-[#EA580C]
          text-white
        `,

        teal: `
          border-[#0D9488]
          bg-[#0D9488]
          text-white
        `,

        cyan: `
          border-[#0891B2]
          bg-[#0891B2]
          text-white
        `,

        indigo: `
          border-[#4F46E5]
          bg-[#4F46E5]
          text-white
        `,

        lime: `
          border-[#65A30D]
          bg-[#65A30D]
          text-white
        `,

        brown: `
          border-[#92400E]
          bg-[#92400E]
          text-white
        `,
      },
    },

    defaultVariants: {
      variant: "default",
    },
  }
);

function Badge({
  className,
  variant,
  asChild = false,
  ...props
}: React.ComponentProps<"span"> &
  VariantProps<typeof badgeVariants> & {
    asChild?: boolean;
  }) {
  const Comp = asChild ? Slot : "span";

  return (
    <Comp
      data-slot="badge"
      data-variant={variant}
      className={cn(
        badgeVariants({ variant }),
        className
      )}
      {...props}
    />
  );
}

export {
  Badge,
  badgeVariants,
};