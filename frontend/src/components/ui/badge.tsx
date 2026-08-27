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
        /* Existing accepted variants */
        default: `
          border-[#D9DEE8]
          bg-white
          text-[#374151]
        `,

        secondary: `
          border-[#E5E7EB]
          bg-[#F8FAFC]
          text-[#475569]
        `,

        success: `
          border-[#BBF7D0]
          bg-[#ECFDF5]
          text-[#15803D]
        `,

        warning: `
          border-[#FDE68A]
          bg-[#FFFBEB]
          text-[#B45309]
        `,

        info: `
          border-[#BFDBFE]
          bg-[#EFF6FF]
          text-[#2563EB]
        `,

        system: `
          border-[#DDD6FE]
          bg-[#F5F3FF]
          text-[#6D28D9]
        `,

        inactive: `
          border-[#E5E7EB]
          bg-[#F9FAFB]
          text-[#6B7280]
        `,

        destructive: `
          border-[#FECACA]
          bg-[#FEF2F2]
          text-[#DC2626]
        `,

        /* Keep accepted subtle variants unchanged */
        outline: `
          border-[#D9DEE8]
          bg-transparent
          text-[#4A5565]
        `,

        ghost: `
          border-transparent
          bg-[#F5F7FB]
          text-[#4A5565]
        `,

        link: `
          border-transparent
          bg-transparent
          p-0
          text-[#4A3FD6]
          underline-offset-4
          hover:underline
        `,

        /* Accepted semantic aliases */
        draft: `
          border-[#64748B]
          bg-[#64748B]
          text-white
        `,

        active: `
          border-[#16A34A]
          bg-[#16A34A]
          text-white
        `,

        approved: `
          border-[#15803D]
          bg-[#15803D]
          text-white
        `,

        rejected: `
          border-[#DC2626]
          bg-[#DC2626]
          text-white
        `,

        locked: `
          border-[#475569]
          bg-[#475569]
          text-white
        `,

        /* Additional solid color variants */
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

        rose: `
          border-[#E11D48]
          bg-[#E11D48]
          text-white
        `,

        violet: `
          border-[#7C3AED]
          bg-[#7C3AED]
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