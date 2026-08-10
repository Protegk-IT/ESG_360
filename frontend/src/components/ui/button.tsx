import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { Slot } from "radix-ui"

import { cn } from "@/lib/utils"

const buttonVariants = cva(
  `
  group/button
  inline-flex
  shrink-0
  items-center
  justify-center
  whitespace-nowrap
  rounded-md
  border
  border-transparent
  bg-clip-padding
  text-sm
  font-medium
  tracking-normal
  transition-all
  duration-200
  ease-in-out
  outline-none
  select-none

  focus-visible:ring-2
  focus-visible:ring-[#4A3FD6]/25
  focus-visible:ring-offset-2

  disabled:pointer-events-none
  disabled:opacity-50

  active:scale-[0.98]

  [&_svg]:pointer-events-none
  [&_svg]:shrink-0
  [&_svg:not([class*='size-'])]:size-4
`,
  {
    variants: {
      variant: {
        /* ======================================================
           ESG PRIMARY
        ====================================================== */

        default:
          `
          bg-[#4A3FD6]
          text-white

          shadow-sm

          hover:bg-[#3F34C8]
          hover:shadow-md
        `,

        /* ======================================================
           OUTLINE
        ====================================================== */

        outline:
          `
          border-[#D9DEE8]
          bg-white
          text-[#111827]

          hover:border-[#4A3FD6]
          hover:bg-[#EEF0FF]
          hover:text-[#4A3FD6]
        `,

        /* ======================================================
           SECONDARY
        ====================================================== */

        secondary:
          `
          border
          border-[#D9DEE8]
          bg-[#F8F9FC]
          text-[#374151]

          hover:bg-[#EEF0FF]
          hover:border-[#C7D2FE]
        `,

        /* ======================================================
           GHOST
        ====================================================== */

        ghost:
          `
          text-[#374151]

          hover:bg-[#EEF0FF]
          hover:text-[#4A3FD6]
        `,

        /* ======================================================
           DESTRUCTIVE
        ====================================================== */

        destructive:
          `
          bg-[#DC2626]
          text-white

          hover:bg-[#B91C1C]
          hover:shadow-md
        `,

        /* ======================================================
           LINK
        ====================================================== */

        link:
          `
          text-[#4A3FD6]

          underline-offset-4

          hover:underline
        `,
      },

      size: {
        default:
          `
          h-10
          px-5
          gap-2
        `,

        xs:
          `
          h-7
          rounded-md
          px-3
          text-xs
        `,

        sm:
          `
          h-9
          rounded-md
          px-4
          text-sm
        `,

        lg:
          `
          h-11
          rounded-lg
          px-6
          text-sm
        `,

        icon:
          `
          size-10
        `,

        "icon-xs":
          `
          size-7
          rounded-md
        `,

        "icon-sm":
          `
          size-9
          rounded-md
        `,

        "icon-lg":
          `
          size-11
          rounded-lg
        `,
      },
    },

    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);

function Button({
  className,
  variant = "default",
  size = "default",
  asChild = false,
  ...props
}: React.ComponentProps<"button"> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean
  }) {
  const Comp = asChild ? Slot.Root : "button"

  return (
    <Comp
      data-slot="button"
      data-variant={variant}
      data-size={size}
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  )
}

export { Button, buttonVariants }
