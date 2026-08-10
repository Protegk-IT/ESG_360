"use client";

import * as React from "react";

import { cn } from "@/lib/utils";

function Input({
  className,
  type,
  ...props
}: React.ComponentProps<"input">) {
  return (
    <input
      type={type}
      data-slot="input"
      className={cn(
        `
        flex

        h-10
        w-full
        min-w-0

        rounded-md

        border
        border-[#D9DEE8]

        bg-white

        px-3
        py-2

        text-sm
        text-[#111827]

        placeholder:text-[#9CA3AF]

        shadow-sm

        transition-all
        duration-200
        ease-in-out

        hover:border-[#BFC6D4]

        focus:outline-none
        focus:border-[#4A3FD6]
        focus:ring-2
        focus:ring-[#4A3FD6]/15

        disabled:cursor-not-allowed
        disabled:bg-[#F8F9FC]
        disabled:text-[#9CA3AF]
        disabled:opacity-70

        aria-invalid:border-[#DC2626]
        aria-invalid:ring-2
        aria-invalid:ring-[#DC2626]/15

        file:border-0
        file:bg-transparent
        file:text-sm
        file:font-medium
        `,
        className
      )}
      {...props}
    />
  );
}

export { Input };