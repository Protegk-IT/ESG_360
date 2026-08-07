import * as React from "react";

import { cn } from "@/lib/utils";

function Textarea({
  className,
  ...props
}: React.ComponentProps<"textarea">) {
  return (
    <textarea
      data-slot="textarea"
      className={cn(
        `
        flex
        min-h-[120px]
        w-full

        resize-y

        rounded-xl

        border
        border-[#D9DEE8]

        bg-white

        px-4
        py-3

        text-sm
        text-[#22243A]

        placeholder:text-[#9CA3AF]

        shadow-sm

        transition-all
        duration-200

        outline-none

        hover:border-[#B8C1D1]

        focus:border-[#4A3FD6]
        focus:ring-4
        focus:ring-[#4A3FD6]/10

        disabled:cursor-not-allowed
        disabled:bg-[#F8F9FC]
        disabled:text-[#9CA3AF]
        disabled:opacity-70
        `,
        className
      )}
      {...props}
    />
  );
}

export { Textarea };