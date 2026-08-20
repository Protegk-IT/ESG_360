import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import {
  cva,
  type VariantProps,
} from "class-variance-authority";

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
  py-[5px]

  text-[10.5px]
  font-bold

  leading-none

  transition-all
  duration-200

  select-none

  focus-visible:outline-none
  focus-visible:ring-2
  focus-visible:ring-[#4A3FD6]
  focus-visible:ring-offset-2

  [&>svg]:h-3.5
  [&>svg]:w-3.5
  [&>svg]:shrink-0
  `,
  {
    variants: {
      variant: {

        /* ==================================================
           DEFAULT
        ================================================== */

        default: `
          border-[#8891A3]
          bg-white
          text-[#22243A]
        `,

        /* ==================================================
           SECONDARY / ACCENT SUBTLE
        ================================================== */

        secondary: `
          border-transparent
          bg-[#ECE9FB]
          text-[#4A3FD6]
        `,

        /* ==================================================
           SUCCESS
        ================================================== */

        success: `
          border-transparent
          bg-[#E6F7EF]
          text-[#167A54]
        `,

        /* ==================================================
           WARNING
        ================================================== */

        warning: `
          border-transparent
          bg-[#FDF1DE]
          text-[#8A5C12]
        `,

        /* ==================================================
           DANGER
        ================================================== */

        destructive: `
          border-transparent
          bg-[#FBE9E8]
          text-[#B3403B]
        `,

        /* ==================================================
           NEUTRAL / LOCKED / INACTIVE
        ================================================== */

        inactive: `
          border-transparent
          bg-[#E9E9EE]
          text-[#22243A]
        `,

        /* ==================================================
           DRAFT
        ================================================== */

        draft: `
          border-transparent
          bg-[#F0F1F6]
          text-[#6B7280]
        `,

        /* ==================================================
           OUTLINE
        ================================================== */

        outline: `
          border-transparent
         bg-[#F3E8FF] text-[#7E22CE]

        `,

        /* ==================================================
           SYSTEM
           -----------------------------------------------
           System is not a semantic token in the design
           reference, so use the accent-subtle treatment.
        ================================================== */

        system: `
          border-transparent
          bg-[#ECE9FB]
          text-[#4A3FD6]
        `,

        /* ==================================================
           INFO
           -----------------------------------------------
           There is no separate INFO token in the official
           design reference. Use secondary/accent treatment.
        ================================================== */

        info: `
          border-transparent
          bg-[#ECE9FB]
          text-[#4A3FD6]
        `,

        /* ==================================================
           GHOST
        ================================================== */

        ghost: `
          border-transparent
           bg-[#EEF0FF]
          text-[#22243A]
        `,

        /* ==================================================
           LINK
        ================================================== */

        link: `
          border-transparent
          bg-transparent
          px-0
          py-0
          text-[#4A3FD6]
          underline-offset-4
          hover:underline
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