"use client";

import * as React from "react";
import { Label as LabelPrimitive } from "radix-ui";

import { cn } from "@/lib/utils";

function Label({
  className,
  ...props
}: React.ComponentProps<typeof LabelPrimitive.Root>) {
  return (
    <LabelPrimitive.Root
      data-slot="label"
      className={cn(
        `
        inline-flex
        items-center
        gap-1.5

        mb-2

        text-sm
        font-medium
        leading-none

        text-[#374151]

        select-none

        transition-colors
        duration-200

        peer-disabled:cursor-not-allowed
        peer-disabled:opacity-50

        group-data-[disabled=true]:pointer-events-none
        group-data-[disabled=true]:opacity-50

        [&[data-required]>span]:text-[#DC2626]
        `,
        className
      )}
      {...props}
    />
  );
}

export { Label };