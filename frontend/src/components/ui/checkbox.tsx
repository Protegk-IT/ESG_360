"use client";

import * as React from "react";
import { Checkbox as CheckboxPrimitive } from "radix-ui";

import { CheckIcon } from "lucide-react";

import { cn } from "@/lib/utils";

function Checkbox({
  className,
  ...props
}: React.ComponentProps<typeof CheckboxPrimitive.Root>) {
  return (
    <CheckboxPrimitive.Root
      data-slot="checkbox"
      className={cn(
        `
        peer

        relative

        flex

        h-[18px]
        w-[18px]

        shrink-0

        items-center
        justify-center

        rounded-md

        border
        border-[#CBD5E1]

        bg-white

        transition-all
        duration-200
        ease-in-out

        hover:border-[#4A3FD6]
        hover:bg-[#EEF0FF]

        focus-visible:outline-none
        focus-visible:ring-2
        focus-visible:ring-[#4A3FD6]/25
        focus-visible:ring-offset-2

        disabled:cursor-not-allowed
        disabled:opacity-50

        data-[state=checked]:border-[#4A3FD6]
        data-[state=checked]:bg-[#4A3FD6]
        data-[state=checked]:text-white
        `,
        className
      )}
      {...props}
    >
      <CheckboxPrimitive.Indicator
        data-slot="checkbox-indicator"
        className="
          flex
          items-center
          justify-center
        "
      >
        <CheckIcon className="h-3.5 w-3.5 stroke-[3]" />
      </CheckboxPrimitive.Indicator>
    </CheckboxPrimitive.Root>
  );
}

export { Checkbox };