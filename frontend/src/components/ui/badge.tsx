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

  min-h-6

  px-2.5
  py-1

  text-[0.6875rem]
  font-semibold
  tracking-[0.01em]

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
        default: `
          border-[#CBD5E1]
          bg-white
          text-[#334155]
        `,

        secondary: `
          border-[#DDD6FE]
          bg-[#F5F3FF]
          text-[#5B21B6]
        `,

        success: `
          border-[#BBE8D4]
          bg-[#EAF8F0]
          text-[#167A54]
        `,

        warning: `
          border-[#F2D8A7]
          bg-[#FDF3E3]
          text-[#8A5C12]
        `,

        info: `
          border-[#C7D2FE]
          bg-[#EEF0FF]
          text-[#4A3FD6]
        `,

        system: `
          border-[#DDD6FE]
          bg-[#ECE9FB]
          text-[#4A3FD6]
        `,

        inactive: `
          border-[#D7DAE1]
          bg-[#F0F1F6]
          text-[#5E6472]
        `,

        destructive: `
          border-[#E8D3D2]
          bg-[#FBE9E8]
          text-[#B3453F]
        `,

        draft: `
          border-[#D7DAE1]
          bg-[#F0F1F6]
          text-[#5E6472]
        `,

        active: `
          border-[#BBE8D4]
          bg-[#EAF8F0]
          text-[#167A54]
        `,

        approved: `
          border-[#BBE8D4]
          bg-[#EAF8F0]
          text-[#167A54]
        `,

        rejected: `
          border-[#E8D3D2]
          bg-[#FBE9E8]
          text-[#B3453F]
        `,

        locked: `
          border-[#D7DAE1]
          bg-[#F0F1F6]
          text-[#5E6472]
        `,

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
